<script setup lang="ts">
//login button
const loginWithOsu = () => {
  const clientId = import.meta.env.VITE_CLIENT_ID
  const redirectUri = import.meta.env.VITE_REDIRECT_URI
  const scope = 'identify public'
  const authUrl = `https://osu.ppy.sh/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}`

  window.location.href = authUrl
}
</script>

<template>
  <router-view />
  <div class="min-h-screen flex items-center justify-center">
    <div class="shadow-black shadow-1x/30 relative w-full max-w-sm p-6 bg-container rounded-4xl">
      <h1 class="absolute left-1/2 -translate-x-1/2 text-pink-400 text-6xl" style="top: -60%">
        maniatool
      </h1>
      <button
        @click="loginWithOsu"
        type="button"
        class="bg-pink-400 hover:bg-pink-500 hover:cursor-pointer text-white outline-pink-400 active:bg-pink-600 focus:outline-pink-600 focus:outline-4 focus:outline-offset-4 focus:outline-pink font-extrabold text-6xl w-full py-3 rounded-3xl"
      >
        Login
      </button>
    </div>
  </div>
</template>

<style scoped></style>
