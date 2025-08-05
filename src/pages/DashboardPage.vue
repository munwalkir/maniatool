<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { isAuthenticated } from '@/auth'

const router = useRouter()
const userData = ref<any>(null)
const loading = ref(true)

onMounted(() => {
  if (!isAuthenticated()) {
    router.push('/login')
    return
  }

  fetchUserData()
})

const fetchUserData = async () => {
  const token = localStorage.getItem('osu_access_token')
  console.log('Token exists:', !!token)

  try {
    loading.value = true

    const response = await fetch('http://localhost:9831/user', {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    console.log('Backend response status:', response.status)
    console.log('Backend response ok:', response.ok)

    if (!response.ok) {
      const errorText = await response.text()
      console.log('Backend error response:', errorText)
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    console.log('USER DATA RECEIVED:', data)
    userData.value = data
  } catch (error) {
    console.error('API Error:', error)
  } finally {
    loading.value = false
  }
}

const formatNumber = (num: number | undefined) => {
  return num ? num.toLocaleString() : 'N/A'
}

const formatPP = (pp: number | undefined) => {
  return pp ? Math.round(pp).toLocaleString() + 'pp' : 'N/A'
}
</script>

<template>
  <nav class="sticky top-0 bg-pink-400 border-container-200">
    <div class="sticky top-0 max-w-screen-xl flex flex-wrap items-center justify-start p-4">
      <a href="/" class="flex items-center space-x-3 rtl:space-x-reverse">
        <img src="/public/mania.ico" alt="Logo" class="w-8 h-8" />
        <span class="text-white text-4xl font-semibold whitespace-nowrap">maniatool</span>
      </a>
    </div>
  </nav>
  <div class="w-full px-4 grid grid-cols-12 gap-4 mt-4">
    <div class="col-span-4 flex flex-col gap-4 h-[89vh]">
      <div class="flex-[2] bg-container rounded-4xl flex items-center justify-start pl-[4vh]">
        <a class="flex items-center gap-6">
          <img :src="userData?.avatar_url" alt="avatar" class="w-24 h-24 rounded-3xl" />

          <!-- horizontal -->
          <div class="flex flex-col">
            <span class="text-3xl font-extrabold text-white">{{ userData?.username }}</span>
            <span class="text-2xl font-semibold text-white"
              >pp: {{ formatPP(userData?.statistics?.pp) }}</span
            >
          </div>

          <!-- vertical -->
          <div class="flex flex-col">
            <span class="text-2xl font-semibold text-white"
              >rank: #{{ formatNumber(userData?.statistics?.global_rank) }}</span
            >
            <span class="text-2xl font-semibold text-white"
              >level: {{ Math.floor(userData?.statistics?.level?.current || 0) }}</span
            >
          </div>
        </a>
      </div>
      <div class="flex-[6.5] bg-container rounded-4xl"></div>
    </div>
    <div class="col-span-4 h-[89vh] bg-container rounded-4xl"></div>
    <div class="col-span-4 h-[89vh] bg-container rounded-4xl"></div>
  </div>
</template>

<style scoped></style>
