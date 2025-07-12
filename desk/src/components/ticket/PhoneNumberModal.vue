<template>
  <Dialog v-model="modelValue" :options="{ title: 'Personal Information' }">
    <template #body-content>
      <div class="space-y-2 text-sm text-gray-800">
        <div><strong>Full Name:</strong> {{ info.full_name }}</div>
        <div><strong>Date of Birth:</strong> {{ info.date_of_birth }}</div>
        <div><strong>NID No:</strong> {{ info.nid_no }}</div>
        <div><strong>Father Name:</strong> {{ info.father_name }}</div>
        <div><strong>Mother Name:</strong> {{ info.mother_name }}</div>
        <div><strong>Address:</strong> {{ info.address }}</div>
        <div><strong>Present Address:</strong> {{ info.present_address }}</div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";

const modelValue = defineModel<boolean>(); // replaces defineProps/emit combo

const props = defineProps({
  info: Object
});
</script>
