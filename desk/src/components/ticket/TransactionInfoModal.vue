<template>
  <Dialog v-model="modelValue" :options="{ title: 'Transaction History', size: '7xl' }">
    <template #body-content>
      <div class="overflow-auto max-h-[70vh]">
        <table class="w-full text-left border border-gray-200 text-sm">
          <thead class="bg-gray-100 text-gray-700">
            <tr>
              <th style="width: 10%;" class="px-4 py-2 border">Time</th>
              <th style="width: 15%;" class="px-4 py-2 border">Type</th>
              <th style="width: 15%;" class="px-4 py-2 border">From</th>
              <th style="width: 15%;" class="px-4 py-2 border">To</th>
              <th style="width: 35%;" class="px-4 py-2 border">Description</th>
              <th style="width: 10%;" class="px-4 py-2 border">Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(tx, index) in records" :key="index" class="hover:bg-gray-50">
              <td class="px-4 py-2 border">{{ tx.time }}</td>
              <td class="px-4 py-2 border">{{ tx.type }}</td>
              <td class="px-4 py-2 border">{{ tx.from }}</td>
              <td class="px-4 py-2 border">{{ tx.to }}</td>
              <td class="px-4 py-2 border">{{ tx.description }}</td>
              <td class="px-4 py-2 border font-semibold text-right">৳ {{ tx.amount }}</td>
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

type TransactionRecord = {
  time: string;
  type: string;
  from: string;
  to: string;
  description: string;
  amount: string;
};

defineProps<{
  records: TransactionRecord[];
}>();
</script>
