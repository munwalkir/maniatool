<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isAuthenticated } from '@/auth'

const router = useRouter()

onMounted(() => {
  if (!isAuthenticated()) {
    router.push('/login')
  }
})
</script>

<template>
  <div class="dashboard">
    <h1>Dashboard</h1>
  </div>
</template>

<style scoped></style>
