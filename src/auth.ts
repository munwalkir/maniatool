export function isAuthenticated(): boolean {
  const token = localStorage.getItem('osu_access_token')
  const expires = parseInt(localStorage.getItem('osu_token_expires') || '0')
  const valid = !!token && Date.now() < expires
  if (!valid) clearAuth()
  return valid
}

export function clearAuth() {
  localStorage.removeItem('osu_access_token')
  localStorage.removeItem('osu_refresh_token')
  localStorage.removeItem('osu_token_expires')
}
