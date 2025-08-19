<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { isAuthenticated } from '@/auth'

const router = useRouter()
const userData = ref<any>(null)
const loading = ref(true)
const showCookiePrompt = ref(false)
const cookieInput = ref('')

onMounted(() => {
  if (!isAuthenticated()) {
    router.push('/login')
    return
  }

  // cookie check
  const cookie = localStorage.getItem('osu_session_cookie')
  if (!cookie) {
    showCookiePrompt.value = true
  } else {
    fetchUserData()
  }
})

const validateAndSaveCookie = () => {
  const cookie = cookieInput.value.trim()

  // cookie validation (ts WONT work)
  if (
    cookie.length < 20 ||
    (!cookie.includes('osu_session=') && !cookie.match(/^[a-zA-Z0-9%]+$/))
  ) {
    alert('Invalid cookie format. Please make sure you copied the full osu_session cookie value.')
    return
  }

  localStorage.setItem('osu_session_cookie', cookie)
  showCookiePrompt.value = false
  fetchUserData()
}

const fetchUserData = async () => {
  const token = localStorage.getItem('osu_access_token')

  try {
    loading.value = true

    const response = await fetch('http://localhost:9831/user', {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
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

const API_BASE = 'http://localhost:9731'
const token = localStorage.getItem('osu_access_token')

fetch(`${API_BASE}/user-scores`, {
  method: 'POST',
  body: JSON.stringify({
    access_token: token,
  }),
  headers: {
    Authorization: `${token}`,
    'Content-Type': 'application/json',
  },
})
</script>

<template>
  <nav class="sticky top-0 bg-pink-400 border-container-200">
    <div class="sticky top-0 max-w-screen-xl flex items-center justify-start p-4 space-x-32">
      <a href="/" class="flex items-center space-x-3 rtl:space-x-reverse">
        <img src="/mania.ico" alt="Logo" class="w-8 h-8" />
        <span class="text-white text-4xl font-semibold whitespace-nowrap">maniatool</span>
      </a>
      <a href="/analyze" class="flex items-center space-x-3 rtl:space-x-reverse">
        <span href="/analyze" class="text-white text-4xl font-semibold whitespace-nowrap"
          >analyze</span
        >
      </a>
    </div>
  </nav>

  <!-- cookie prompt -->
  <div
    v-if="showCookiePrompt"
    class="fixed inset-0 bg-background bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
      <h3 class="text-lg font-bold mb-4">osu! Cookie Needed</h3>
      <p class="text-sm text-gray-600 mb-4">
        We need your osu! session cookie to download beatmaps. It's stored locally and only used for
        beatmap downloads.
      </p>
      <input
        v-model="cookieInput"
        type="password"
        placeholder="osu_session=..."
        class="w-full p-3 border border-pink-600 outline-0 rounded mb-4"
      />
      <button
        @click="validateAndSaveCookie"
        :disabled="!cookieInput.trim()"
        class="w-full bg-pink-400 text-white p-3 rounded hover:bg-pink-500 cursor-pointer disabled:cursor-auto disabled:bg-gray-300"
      >
        Save Cookie
      </button>
    </div>
  </div>

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
