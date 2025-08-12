# Copyright (c) 2023, Frappe Technologies Pvt. Ltd.
# MIT License. See license.txt

from __future__ import unicode_literals

import json
import re
from contextlib import suppress
from copy import deepcopy
from math import isclose
from typing import TYPE_CHECKING

import frappe
from bs4 import BeautifulSoup, PageElement
from frappe.utils import cstr, strip_html_tags, update_progress_bar
from frappe.utils.caching import redis_cache
from frappe.utils.synchronization import filelock

# ---- Redis / RediSearch imports: support both redis-py 4.x (camel) and 5.x (snake) ----
try:
    from redis.commands.search.field import TagField, TextField
    try:
        # redis-py 4.x
        from redis.commands.search.indexDefinition import IndexDefinition
    except ImportError:
        # redis-py 5.x
        from redis.commands.search.index_definition import IndexDefinition
    from redis.commands.search.query import Query
    from redis.exceptions import ResponseError
except Exception:
    # Fallback to legacy redisearch client if present (optional)
    from redisearch import TagField, TextField, IndexDefinition, Query  # type: ignore
    from redis import ResponseError  # type: ignore

from helpdesk.utils import is_agent

if TYPE_CHECKING:
    from helpdesk.helpdesk.doctype.hd_settings.hd_settings import HDSettings

NUM_RESULTS = 5

STOPWORDS = [
    "a", "is", "the", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if",
    "in", "into", "it", "no", "not", "of", "on", "or", "such", "that", "their", "then",
    "there", "these", "they", "this", "to", "was", "will", "with", "how", "what",
    "where", "when", "i", "you", "me", "do", "has", "been", "urgent", "want",
]


@redis_cache(3600 * 24)
def get_stopwords():
    return STOPWORDS + frappe.get_all("HD Stopword", {"enabled": True}, pluck="name")


@redis_cache(1800)
def get_synonym_words() -> list[str]:
    ret = frappe.get_all("HD Synonym", ["name"], as_list=True) + frappe.get_all(
        "HD Synonyms", ["name"], as_list=True
    )
    return [r[0] for r in ret]


class Search:
    unsafe_chars = re.compile(r"[\[\]{}<>+!-]")

    def __init__(self, index_name, prefix, schema) -> None:
        self.redis = frappe.cache()
        self.index_name = index_name
        self.prefix = prefix
        self.schema = [frappe._dict(field) for field in schema]
        self._index_exists = None  # lazy-evaluated

    def create_index(self):
        index_def = IndexDefinition(prefix=[f"{self.redis.make_key(self.prefix).decode()}:" ])
        schema = []
        for field in self.schema:
            kwargs = {k: v for k, v in field.items() if k in ["weight", "sortable", "no_index", "no_stem"]}
            if field.type == "tag":
                schema.append(TagField(field.name, **kwargs))
            else:
                schema.append(TextField(field.name, **kwargs))

        self.redis.ft(self.index_name).create_index(
            schema,
            definition=index_def,
            stopwords=get_stopwords(),
        )
        self.add_synonyms()
        self._index_exists = True

    def add_synonyms(self):
        # Note: using the word as the synonym group id; adjust if you want numeric groups.
        for word, synonym in frappe.get_all("HD Synonym", ["parent", "name"], as_list=True):
            # synupdate(groupid, skipinitialscan, *terms)
            self.redis.ft(self.index_name).synupdate(word, True, word, synonym)

    def add_document(self, id, doc):
        doc = frappe._dict(doc)
        doc_id = self.redis.make_key(f"{self.prefix}:{id}").decode()
        mapping = {field.name: cstr(doc[field.name]) for field in self.schema if field.name in doc}
        if self.index_exists():
            self.redis.ft(self.index_name).add_document(doc_id, replace=True, **mapping)

    def remove_document(self, id):
        key = self.redis.make_key(f"{self.prefix}:{id}").decode()
        if self.index_exists():
            self.redis.ft(self.index_name).delete_document(key)

    def search(self, query, start=0, page_length=NUM_RESULTS, highlight=False):
        query = self.clean_query(query)
        q = Query(query).paging(start, page_length)
        if highlight:
            q = q.highlight()

        q.summarize(fields=["description"])
        q.scorer("DISMAX")

        # Avoid passing None (redis-py expects int dialect, default is fine)
        try:
            q.dialect(2)
        except Exception:
            pass

        try:
            result = self.redis.ft(self.index_name).search(q)
        except ResponseError:
            # likely index missing: try once to create
            self.create_index()
            result = self.redis.ft(self.index_name).search(q)

        # duration may not exist on all client versions
        duration = getattr(result, "duration", None) or getattr(result, "execution_time", None)
        out = frappe._dict(docs=[], total=result.total, duration=duration)
        for doc in result.docs:
            id = doc.id.split(":", 1)[1]
            _doc = frappe._dict(doc.__dict__)
            _doc.id = id
            _doc.payload = json.loads(doc.payload) if getattr(doc, "payload", None) else None
            out.docs.append(_doc)
        return out

    def clean_query(self, query):
        query = query.strip().replace("-*", "*")
        query = self.unsafe_chars.sub(" ", query)
        return query.strip().lower()

    def spellcheck(self, query, **kwargs):
        return self.redis.ft(self.index_name).spellcheck(query, **kwargs)

    def drop_index(self):
        with suppress(ResponseError):  # Index may not exist
            self.redis.ft(self.index_name).dropindex(delete_documents=True)

    def get_count(self, doctype):
        raise NotImplementedError

    def num_records(self) -> int:
        return sum(self.get_count(doctype) for doctype in self.DOCTYPE_FIELDS.keys())

    def index_exists(self):
        if self._index_exists is not None:
            return self._index_exists
        self._index_exists = False
        with suppress(ResponseError):
            ftinfo = self.redis.ft(self.index_name).info()
            if isclose(int(ftinfo.get("num_docs", 0)), self.num_records(), rel_tol=0.1):
                self._index_exists = True
        return self._index_exists


class HelpdeskSearch(Search):
    DOCTYPE_FIELDS = {
        "HD Ticket": [
            "name", "subject", "description", "agent_group", "modified", "creation",
        ],
        "HD Article": [
            "name", "title", "content", "modified", "creation",
            "category.category_name as category",
        ],
    }

    def __init__(self):
        settings: "HDSettings" = frappe.get_cached_doc("HD Settings")
        schema = [
            {"name": "name", "weight": settings.name_weight or 1},
            {"name": "subject", "weight": settings.subject_weight or 6},
            {"name": "description", "weight": settings.description_weight or 5},
            {"name": "headings", "weight": settings.headings_weight or 8},
            {"name": "team", "type": "tag"},
            {"name": "modified", "sortable": True},
            {"name": "creation", "sortable": True},
        ]
        super().__init__("helpdesk_idx", "search_doc", schema)

    def build_index(self):
        self.drop_index()
        self.create_index()
        records = self.get_records("HD Ticket") + self.get_records("HD Article")
        total = len(records)
        for i, doc in enumerate(records, start=1):
            self.index_doc(doc)
            if not hasattr(frappe.local, "request"):
                update_progress_bar("Indexing", i, total)

    def index_doc(self, doc):
        id = f"{doc.doctype}:{doc.name}"
        fields = None
        if doc.doctype == "HD Ticket":
            fields = {
                "doctype": doc.doctype,
                "name": doc.name,
                "subject": doc.subject,
                "team": doc.agent_group,
                "modified": doc.modified,
                # (optional) add description/headings here if you want to search inside ticket body
            }
        elif doc.doctype == "HD Article":
            fields = {
                "doctype": doc.doctype,
                "name": doc.name,
                "subject": doc.title,
                "description": strip_html_tags(doc.content),
                "headings": doc.headings,
                "modified": doc.modified,
            }
        if fields:
            self.add_document(id, fields)

    def remove_doc(self, doc):
        key = f"{doc.doctype}:{doc.name}"
        self.remove_document(key)

    def extract_headings(self, content: str | None) -> str:
        try:
            soup = BeautifulSoup(content, "html.parser")
        except TypeError:
            ret = []
        else:
            ret = []
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                for heading in soup.find_all(tag):
                    ret.append(heading.text)
        return json.dumps(ret)

    def get_sections(self, content: str) -> list[tuple[str, str]]:
        try:
            soup = BeautifulSoup(content, "html.parser")
        except TypeError:
            return []
        else:
            sections = []
            tag: PageElement
            section = ""
            heading = ""
            for tag in soup.find_all():
                if tag.name in ["p", "blockquote", "code"]:
                    section += tag.text + "\n"
                elif tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    sections.append((heading, section))
                    section = ""
                    heading = tag.text
            sections.append((heading, section))
            return sections

    def scrub(self, text: str):
        # For permalink
        return re.sub(r"[^a-zA-Z0-9]+", "-", text).lower()

    def get_count(self, doctype):
        if doctype == "HD Ticket":
            return frappe.db.count(doctype)
        if doctype == "HD Article":
            return len(self.get_records(doctype))
        return 0

    def get_records(self, doctype):
        records = []
        filters = {"status": "Published"} if doctype == "HD Article" else {}
        for d in frappe.db.get_all(doctype, filters=filters, fields=self.DOCTYPE_FIELDS[doctype]):
            d.doctype = doctype
            if doctype == "HD Article":
                for heading, section in self.get_sections(d.content):
                    cd = deepcopy(d)
                    cd.name = d.name + f"#{self.scrub(heading)}"
                    cd.content = section
                    cd.headings = heading
                    records.append(cd)
            else:  # HD Ticket
                d.headings = self.extract_headings(d.description)
                records.append(d)
        return records


@frappe.whitelist()
def search(query, only_articles=False) -> list[dict[str, list[dict]]]:
    s = HelpdeskSearch()
    query = s.clean_query(query)
    query_parts = query.split()
    q = ""
    for part in query_parts:
        if part in get_synonym_words():
            q += f" {part}"
            continue
        if part in get_stopwords():
            continue
        if len(part) > 3:
            q += f" %{part}%"
        else:
            q += f" {part}*"

    result = s.search(q, start=0, highlight=True)
    groups: dict[str, list] = {}
    for r in result.docs:
        doctype, name = r.id.split(":")
        r.doctype = doctype
        r.name = name
        if doctype == "HD Ticket" and not only_articles:
            # FIX: don't append an empty list for non-agents; just skip
            if not is_agent():
                continue
            groups.setdefault("Tickets", []).append(r)
        elif doctype == "HD Article":
            groups.setdefault("Articles", []).append(r)

    return [{"title": k, "items": v} for k, v in groups.items()]


@frappe.whitelist()
@filelock("helpdesk_search_indexing", timeout=1)
def build_index():
    frappe.cache().set_value("helpdesk_search_indexing_in_progress", True)
    s = HelpdeskSearch()
    s.build_index()
    frappe.cache().set_value("helpdesk_search_indexing_in_progress", False)


def build_index_in_background():
    if not frappe.cache().get_value("helpdesk_search_indexing_in_progress"):
        frappe.enqueue(build_index, queue="long")


def build_index_if_not_exists():
    s = HelpdeskSearch()
    if not s.index_exists():
        build_index()


@filelock("helpdesk_corpus_download", timeout=1, is_global=True)
def download_corpus():
    from nltk import data, download

    try:
        data.find("taggers/averaged_perceptron_tagger_eng.zip")
        data.find("tokenizers/punkt_tab.zip")
        data.find("corpora/brown.zip")
    except LookupError:
        download("averaged_perceptron_tagger_eng")
        download("punkt_tab")
        download("brown")
