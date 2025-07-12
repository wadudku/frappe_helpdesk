<template>
  <div class="flex flex-1 flex-col overflow-hidden overflow-y-auto border-b">
    <div
      v-for="field in fields"
      :key="field.fieldname"
    >
      
      <div v-if="field.fieldname === 'custom_phone_number'">
        <div data-v-dea72048="" class="flex gap-2 px-6 pb-1 leading-5 first:mt-3 items-baseline">
          <div data-v-dea72048="" class="w-[106px] shrink-0 truncate text-sm text-gray-600" data-state="closed" data-grace-area-trigger="">
            {{ field.label }}
          </div>
          <div data-v-dea72048="" class="-m-0.5 min-h-[28px] flex-1 items-center overflow-hidden p-0.5 text-base">
            <div data-v-dea72048="" class="space-y-1.5 form-control" placeholder="Add Ticket Type" autocomplete="off">
                <div>
                  <div class="flex w-full">
                      <div class="w-full">
                        <div class="flex items-center">
                            <a
                                href="#"
                                style="margin-left: 10px;"
                                class="overflow-hidden text-ellipsis whitespace-nowrap text-base leading-5 underline"
                                @click.prevent="() => openPersonalInfoModal(ticket[field.fieldname])"
                                >
                                {{ ticket[field.fieldname] }}
                            </a>
                        </div>
                      </div>
                  </div>
                </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="field.fieldname === 'custom_transaction_id'">
        <div data-v-dea72048="" class="flex gap-2 px-6 pb-1 leading-5 first:mt-3 items-baseline">
          <div data-v-dea72048="" class="w-[106px] shrink-0 truncate text-sm text-gray-600" data-state="closed" data-grace-area-trigger="">
            {{ field.label }}
          </div>
          <div data-v-dea72048="" class="-m-0.5 min-h-[28px] flex-1 items-center overflow-hidden p-0.5 text-base">
            <div data-v-dea72048="" class="space-y-1.5 form-control" placeholder="Add Ticket Type" autocomplete="off">
                <div>
                  <div class="flex w-full">
                      <div class="w-full">
                        <div class="flex items-center">
                            <a
                                href="#"
                                style="margin-left: 10px;"
                                class="overflow-hidden text-ellipsis whitespace-nowrap text-base leading-5 underline"
                                @click.prevent="()=> openTransactionModal(ticket[field.fieldname])"
                                >
                                {{ ticket[field.fieldname] }}
                            </a>
                        </div>
                      </div>
                  </div>
                </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="field.fieldname === 'custom_user_attachment'">
        <div data-v-dea72048="" class="flex gap-2 px-6 pb-1 leading-5 first:mt-3 items-baseline">
          <div data-v-dea72048="" class="w-[106px] shrink-0 truncate text-sm text-gray-600" data-state="closed" data-grace-area-trigger="">
            {{ field.label }}
          </div>
          <div data-v-dea72048="" class="-m-0.5 min-h-[28px] flex-1 items-center overflow-hidden p-0.5 text-base">
            <div data-v-dea72048="" class="space-y-1.5 form-control" placeholder="Add Ticket Type" autocomplete="off">
                <div>
                  <div class="flex w-full">
                      <div class="w-full">
                        <div class="flex items-center">
                            <a
                              :href="getFileUrl(ticket[field.fieldname])"
                              class="text-blue-600 underline"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                               📎 {{ getFileName(ticket[field.fieldname]) }}
                            </a>
                        </div>
                      </div>
                  </div>
                </div>
            </div>
          </div>
        </div>
      </div>

      <UniInput2
        v-else
        :field="field"
        :value="ticket[field.fieldname]"
        @change="(data) => update(data.fieldname, data.value)"
      />
    </div>
    <PersonalInfoModal v-model="showPersonalInfoModal" :info="personalInfo" />
    <TransactionInfoModal v-model="showTransactionModal" :records="transactionRecords" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { toast, call } from "frappe-ui";
import UniInput2 from "../UniInput2.vue";
import PersonalInfoModal from "./PersonalInfoModal.vue";
import TransactionInfoModal from "./TransactionInfoModal.vue";

const emit = defineEmits(["update"]);
const props = defineProps({ ticket: Object });

const fields = computed(() => props.ticket.fields);

function update(field, value, event = null) {
  if (field === "subject" && value === "") {
    toast.error("Subject is required");
    event.target.value = props.ticket.subject;
    return;
  }
  emit("update", { field, value });
}

// Phone number wise data gathering
const showPersonalInfoModal = ref(false);
const personalInfo = ref({});

async function openPersonalInfoModal(phoneNo: string) {
  try {
    const data = await call(
      "helpdesk.helpdesk.doctype.hd_ticket.api.get_personal_infos",
      { "phone_no" : phoneNo }
    );
    personalInfo.value = data;
    showPersonalInfoModal.value = true;
  } catch (err) {
    toast.error("Failed to load personal info.");
  }
}

//Transaction Id wise data gathering
const showTransactionModal = ref(false);
const transactionRecords = ref([]);

async function openTransactionModal(transactionId: string) {
  try {
    const data = await call(
      "helpdesk.helpdesk.doctype.hd_ticket.api.get_transaction_infos",
      {"transactionId": transactionId}
    );
    transactionRecords.value = data;
    showTransactionModal.value = true;
  } catch (err) {
    toast.error("Failed to load transaction info.");
  }
}

function getFileUrl(filePath: string) {
  return `/api/method/frappe.handler.download_file?file_url=${encodeURIComponent(filePath)}`
}

const getFileName = (filePath) => filePath.split("/").pop();
</script>
