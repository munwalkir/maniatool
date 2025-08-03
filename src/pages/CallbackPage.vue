<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(async () => {
  const code = route.query.code as string | undefined
  if (!code) {
    alert('No code found in URL')
    router.push('/')
    return
  }

  try {
    const res = await fetch(`http://localhost:9931/callback?code=${code}`)
    if (!res.ok) throw new Error('Token exchange failed')

    const data = await res.json()
    console.log('Tokens:', data)

    localStorage.setItem('osu_access_token', data.access_token)
    localStorage.setItem('osu_refresh_token', data.refresh_token)
    localStorage.setItem('osu_token_expires', (Date.now() + data.expires_in * 1000).toString())

    router.push('/')
  } catch (err) {
    alert('Login failed: ' + (err as Error).message)
    router.push('/')
  }
})
</script>

<template>
  <div class="flex justify-center items-center min-h-screen">
    <p>Logging in, please wait...</p>
  </div>
</template>
