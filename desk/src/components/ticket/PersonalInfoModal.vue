<template>
  <Dialog v-model="modelValue" :options="{ title: 'Personal Information', size: '3xl' }">
    <template #body-content>
      <div class="overflow-auto max-h-[70vh]">
        <table class="w-full text-left border border-gray-200 text-sm">
          <tbody>
            <tr>
              <td rowspan="5">
                <img :src="info.profile_image" style="width: 100%; height: 200px; border: 1px solid black; padding: 5px;" />
              </td>
              <td width="70%" style="border: 1px solid black;">
                <strong style="margin-left: 10px;">Full Name:</strong> {{ info.full_name }}
              </td>
            </tr>
            <tr>
              <td width="70%" style="border: 1px solid black;">
                <strong style="margin-left: 10px;">Date of Birth:</strong> {{ info.date_of_birth }}
              </td>
            </tr>
            <tr>
              <td width="70%" style="border: 1px solid black;">
                <strong style="margin-left: 10px;">NID No:</strong> {{ info.nid_no }}
              </td>
            </tr>
            <tr>
              <td width="70%" style="border: 1px solid black;">
                <strong style="margin-left: 10px;">Father Name:</strong> {{ info.father_name }}
              </td>
            </tr>
            <tr>
              <td width="70%" style="border: 1px solid black;">
                <strong style="margin-left: 10px;">Mother Name:</strong> {{ info.mother_name }}
              </td>
            </tr>
          </tbody>
        </table>
        <table style="margin-top: 20px;" class="w-full text-left border border-gray-200 text-sm">
            <tr>
              <td style="padding: 10px; border: 1px solid black;">
                <strong>Address:</strong> {{ info.address }}
              </td>
            </tr>
            <tr>
              <td style="padding: 10px; border: 1px solid black;">
                <strong>Present Address:</strong> {{ info.present_address }}
              </td>
            </tr>
        </table>
        <table style="margin-top: 20px;" class="w-full text-left border border-gray-200 text-sm">
          <tbody>
            <tr>
              <td>
                <img :src="info.nid_front" style="width: 100%; height: 300px; padding: 5px; border: 1px solid black;" />
              </td>
              <td>
                <img :src="info.nid_back" style="width: 100%; height: 300px; padding: 5px; border: 1px solid black;" />
              </td>
            </tr>
          </tbody>
        </table>
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
