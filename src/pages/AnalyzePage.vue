<template>
  <nav class="sticky top-0 bg-pink-400 border-container-200">
    <div class="sticky top-0 max-w-screen-xl flex items-center justify-start p-4 space-x-32">
      <router-link to="/" class="flex items-center space-x-3 rtl:space-x-reverse">
        <img src="/mania.ico" alt="Logo" class="w-8 h-8" />
        <span class="text-white text-4xl font-semibold whitespace-nowrap">maniatool</span>
      </router-link>
      <router-link to="/analyze" class="flex items-center space-x-3 rtl:space-x-reverse">
        <span class="text-white text-4xl font-semibold whitespace-nowrap">analyze</span>
      </router-link>
    </div>
  </nav>

  <div class="w-full px-4 grid grid-cols-12 gap-4 mt-4">
    <!-- analysis -->
    <div class="col-span-8 h-[89vh] bg-container rounded-4xl p-6 overflow-auto no-scrollbar">
      <div class="max-w-4xl mx-auto text-white">
        <div class="mb-6">
          <h1 class="text-3xl font-bold text-center mb-1">difficulty analyzer</h1>
          <p class="text-gray-400 text-center">
            Paste a beatmapset ID, select a difficulty and analyze (only 4K maps).
          </p>
        </div>

        <!-- input n load -->
        <div class="mb-4">
          <div class="flex gap-3">
            <input
              v-model.number="beatmapId"
              type="number"
              placeholder="Enter beatmapset ID (e.g. 2055332)"
              class="[appearance:textfield] flex-1 px-4 py-3 bg-analysis border border-gray-600 rounded-lg focus:outline-none focus:border-pink-400 focus:ring-1 focus:ring-pink-400 transition-colors"
              @keyup.enter="loadDifficulties"
            />
            <select
              v-model="selectedRate"
              id="rate"
              name="rate"
              aria-label="Rate"
              class="w-20 text-center appearance-none rounded-lg bg-analysis py-1.5 pr-3 pl-3 text-white border border-gray-600 *:bg-analysis placeholder:text-gray-500 focus:outline-none focus:border-pink-400 focus:ring-1 focus:ring-pink-400 transition-colors text-base"
            >
              <option value="0.75">HT</option>
              <option value="1.0">NM</option>
              <option value="1.5">DT</option>
            </select>
            <button
              type="button"
              @click="loadDifficulties"
              :disabled="!beatmapId || loading"
              class="px-6 py-3 bg-pink-400 hover:bg-pink-500 hover:cursor-pointer active:bg-pink-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
            >
              <span v-if="loading">Loading...</span>
              <span v-else>Load</span>
            </button>
          </div>
        </div>

        <div v-if="error" class="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg">
          <p class="text-red-200">{{ error }}</p>
        </div>

        <div v-if="saveSuccess" class="mb-4 p-3 bg-green-900/50 border border-green-700 rounded-lg">
          <p class="text-green-200">{{ saveSuccess }}</p>
        </div>

        <!-- beatmap -->
        <div v-if="beatmapset" class="mb-6 p-6 bg-analysis rounded-lg">
          <div class="flex items-center gap-4 mb-4">
            <div class="flex-1">
              <h2 class="text-xl font-bold">{{ beatmapset.artist }} - {{ beatmapset.title }}</h2>
              <p class="text-gray-400">Mapped by {{ beatmapset.creator }}</p>
            </div>
            <div class="text-right text-sm text-gray-400">
              <p>{{ beatmapset.total_found }} mania difficulties</p>
            </div>
          </div>

          <div class="space-y-2">
            <p class="text-sm font-medium text-gray-300 mb-2">Select Difficulty:</p>

            <div
              v-if="
                beatmapset.beatmapsets &&
                beatmapset.beatmapsets[0] &&
                beatmapset.beatmapsets[0].difficulties.length
              "
            >
              <button
                v-for="(diff, index) in beatmapset.beatmapsets[0].difficulties"
                :key="index"
                type="button"
                @click="selectDifficulty(diff)"
                :class="[
                  'w-full text-left p-3 rounded-lg border transition-colors mb-2',
                  selectedDifficulty && selectedDifficulty.difficulty_name === diff.difficulty_name
                    ? 'bg-pink-700/50 border-pink-400 text-white'
                    : 'bg-button border-gray-600 hover:bg-gray-600',
                ]"
              >
                <div class="flex justify-between items-center">
                  <div class="flex items-center gap-2">
                    <span class="font-medium">{{ diff.difficulty_name }}</span>
                    <span class="text-gray-400">({{ diff.key_count }}K)</span>
                    <span
                      :class="[
                        'px-2 py-1 rounded-md text-xs font-bold border',
                        getDifficultyColor(findStarRatingField(diff)).bg,
                        getDifficultyColor(findStarRatingField(diff)).text,
                        getDifficultyColor(findStarRatingField(diff)).border,
                      ]"
                    >
                      {{ formatOsuSR(findStarRatingField(diff)) }}★
                    </span>
                  </div>
                  <span class="text-sm text-gray-400">{{ diff.hit_objects }} objects</span>
                </div>
              </button>
            </div>
            <div v-else class="text-gray-400">No difficulties found.</div>
          </div>

          <div v-if="selectedDifficulty" class="mt-4 pt-4 border-t border-gray-600">
            <button
              type="button"
              @click="analyzeDifficulty"
              :disabled="analyzing"
              class="w-full px-6 py-3 hover:cursor-pointer bg-pink-400 hover:bg-pink-500 active:bg-pink-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
            >
              <span v-if="analyzing">Analyzing...</span>
              <span v-else
                >Analyze {{ selectedDifficulty.difficulty_name }} ({{ getRateDisplayName() }})</span
              >
            </button>
          </div>
        </div>

        <!-- results -->
        <div v-if="analysis" class="space-y-6">
          <!-- banner -->
          <div
            class="relative p-6 rounded-lg overflow-hidden min-h-[150px] flex items-center"
            :style="{
              backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url(https://assets.ppy.sh/beatmaps/${beatmapId}/covers/cover@2x.jpg)`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              backgroundRepeat: 'no-repeat',
            }"
          >
            <div class="flex items-center justify-between w-full z-10">
              <div class="flex-1">
                <h2 class="text-2xl font-bold text-white drop-shadow-lg">
                  {{ analysis.artist }} - {{ analysis.title }}
                </h2>
                <p class="text-gray-200 drop-shadow-md">
                  "{{ analysis.difficulty_name }}" by {{ analysis.creator }}
                </p>
                <p class="text-sm text-gray-300 mt-1 drop-shadow-md">
                  {{ analysis.key_count }}K • {{ analysis.hit_objects }} objects •
                  {{ getRateDisplayName(analysis.rate) }}
                </p>
              </div>
              <div class="text-right">
                <div class="text-3xl font-bold text-pink-400 drop-shadow-lg">
                  {{ formatDecimal(analysis.overall) }}
                </div>
                <div class="text-sm text-gray-200 drop-shadow-md">Overall</div>
              </div>
            </div>
          </div>

          <!-- stats -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="p-4 bg-analysis rounded-lg" v-for="stat in statsToShow" :key="stat.name">
              <div class="text-center">
                <div :class="`text-2xl font-bold ${stat.color}`">
                  {{ formatDecimal(stat.value) }}
                </div>
                <div class="text-sm text-gray-400 mt-1">{{ stat.name }}</div>
              </div>
            </div>
          </div>

          <div class="p-4 bg-analysis rounded-lg">
            <div class="flex justify-between items-center text-sm text-gray-400">
              <span>Analysis completed at {{ formattedAnalyzedAt }}</span>
              <div class="flex items-center gap-4">
                <span :class="analysis.success ? 'text-green-400' : 'text-red-400'">
                  {{ analysis.success ? '✓ Success' : '✗ Failed' }}
                </span>
                <span class="text-green-400"> ✓ Auto-saved </span>
                <span
                  :class="[
                    'px-2 py-1 rounded-md text-xs font-bold border',
                    getDifficultyColor(getCurrentStarRating()).bg,
                    getDifficultyColor(getCurrentStarRating()).text,
                    getDifficultyColor(getCurrentStarRating()).border,
                  ]"
                >
                  osu!SR: {{ formatOsuSR(getCurrentStarRating()) }}★
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- sidebar -->
    <div class="col-span-4 h-[89vh] bg-container rounded-4xl p-6 overflow-auto">
      <div class="text-white">
        <h3 class="text-xl font-semibold mb-3">Account</h3>
        <div v-if="userLoading" class="text-gray-400">Loading account...</div>
        <div v-else-if="userData">
          <p class="text-sm text-gray-300">{{ userData.username }}</p>
          <p class="text-xs text-gray-500">ID: {{ userData.id }}</p>
        </div>
        <div v-else class="text-gray-400">No account info</div>

        <hr class="my-4 border-gray-700" />

        <h3 class="text-xl font-semibold mb-3">Rate Info</h3>
        <div class="text-sm text-gray-400 space-y-1">
          <div class="flex justify-between">
            <span>HT (Half Time):</span>
            <span class="text-gray-300">0.75x</span>
          </div>
          <div class="flex justify-between">
            <span>NM (No Mod):</span>
            <span class="text-gray-300">1.0x</span>
          </div>
          <div class="flex justify-between">
            <span>DT (Double Time):</span>
            <span class="text-gray-300">1.5x</span>
          </div>
        </div>
        <div class="text-xs text-gray-500 mt-2">
          Current: <span class="text-gray-300">{{ getRateDisplayName() }}</span>
        </div>

        <hr class="my-4 border-gray-700" />

        <h3 class="text-xl font-semibold mb-3">Saved Data</h3>
        <div class="text-sm text-gray-400 space-y-2">
          <div class="flex justify-between">
            <span>Total Saved:</span>
            <span class="text-pink-400 font-medium">{{ savedAnalyses.length }}</span>
          </div>

          <!-- rs buttons -->
          <div class="space-y-2">
            <button
              type="button"
              @click="viewSavedAnalyses"
              class="w-full px-4 py-2 bg-pink-400 hover:bg-pink-500 hover:cursor-pointer active:bg-pink-600 rounded-lg font-medium transition-colors text-white text-sm"
            >
              View Saved ({{ savedAnalyses.length }})
            </button>
            <button
              type="button"
              @click="exportAnalyses"
              :disabled="savedAnalyses.length === 0"
              class="w-full px-4 py-2 bg-button hover:bg-gray-600 hover:cursor-pointer active:bg-gray-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors text-white text-sm"
            >
              Export JSON
            </button>
            <button
              type="button"
              @click="clearSavedAnalyses"
              :disabled="savedAnalyses.length === 0"
              class="w-full px-4 py-2 bg-button hover:bg-gray-600 hover:cursor-pointer active:bg-gray-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors text-white border border-red-400/30 hover:border-red-400/50 text-sm"
            >
              Clear All
            </button>
          </div>

          <!-- saves preview -->
          <div v-if="savedAnalyses.length > 0" class="max-h-40 overflow-y-auto space-y-2 mt-4">
            <div
              v-for="(saved, index) in savedAnalyses.slice(-3)"
              :key="index"
              class="text-xs text-gray-500 p-3 bg-analysis rounded-lg border border-gray-700"
            >
              <div class="font-medium text-gray-300 mb-1">{{ saved.title }}</div>
              <div class="text-gray-400">{{ saved.difficulty_name }} • {{ saved.key_count }}K</div>
              <div class="text-pink-400 font-medium mt-1">
                {{ formatDecimal(saved.our_overall_rating) }} Overall
              </div>
              <div
                :class="[
                  'text-xs mt-1 px-2 py-1 rounded-md font-bold border inline-block',
                  getDifficultyColor(saved.osu_star_rating).bg,
                  getDifficultyColor(saved.osu_star_rating).text,
                  getDifficultyColor(saved.osu_star_rating).border,
                ]"
              >
                osu!SR: {{ formatOsuSR(saved.osu_star_rating) }}★
              </div>
            </div>
            <div
              v-if="savedAnalyses.length > 3"
              class="text-xs text-gray-500 text-center py-2 bg-analysis rounded-lg"
            >
              ... and {{ savedAnalyses.length - 3 }} more
            </div>
          </div>
          <div
            v-else
            class="text-gray-500 text-center py-4 bg-analysis rounded-lg border border-dashed border-gray-600 mt-4"
          >
            No saved analyses
          </div>
        </div>

        <hr class="my-4 border-gray-700" />

        <h3 class="text-xl font-semibold mb-3">Logs</h3>
        <div class="text-sm text-gray-400">
          Status:
          <span :class="loading ? 'text-yellow-300' : 'text-gray-300'">{{
            loading ? 'fetching' : 'idle'
          }}</span>
        </div>
        <div class="text-sm text-gray-400 mt-2">
          Analyze:
          <span :class="analyzing ? 'text-yellow-300' : 'text-gray-300'">{{
            analyzing ? 'running' : 'idle'
          }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- saved analysis view -->
  <div
    v-if="showSavedModal"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click="showSavedModal = false"
  >
    <div
      class="bg-container rounded-4xl p-6 max-w-4xl max-h-[80vh] w-[90vw] overflow-hidden"
      @click.stop
    >
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-white">Saved Analyses</h2>
        <div class="flex items-center gap-4">
          <span class="text-gray-400">{{ savedAnalyses.length }} total</span>
          <button
            type="button"
            @click="showSavedModal = false"
            class="text-gray-400 hover:text-white text-3xl font-light hover:bg-gray-700 rounded-lg p-2 transition-colors"
          >
            ×
          </button>
        </div>
      </div>

      <div class="overflow-auto max-h-[calc(80vh-120px)]">
        <div v-if="savedAnalyses.length === 0" class="text-gray-400 text-center py-12">
          <div class="text-6xl mb-4">📊</div>
          <p class="text-lg">No saved analyses yet</p>
          <p class="text-sm mt-2">Analyze some maps and save them to see them here!</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="(saved, index) in savedAnalyses"
            :key="index"
            class="bg-analysis p-6 rounded-lg border border-gray-600"
          >
            <div class="flex justify-between items-start mb-4">
              <div class="flex-1">
                <h3 class="text-xl font-bold text-white mb-1">{{ saved.title }}</h3>
                <p class="text-gray-300 text-lg">{{ saved.artist }}</p>
                <div class="flex items-center gap-4 mt-2 text-sm text-gray-400">
                  <span class="bg-button px-3 py-1 rounded">{{ saved.difficulty_name }}</span>
                  <span class="bg-button px-3 py-1 rounded">{{ saved.key_count }}K</span>
                  <span class="bg-button px-3 py-1 rounded">{{
                    getRateDisplayName(saved.rate)
                  }}</span>
                  <span class="bg-button px-3 py-1 rounded">{{ saved.hit_objects }} objects</span>
                </div>
              </div>
              <div class="text-right">
                <div class="text-3xl font-bold text-pink-400 mb-1">
                  {{ formatDecimal(saved.our_overall_rating) }}
                </div>
                <div class="text-sm text-gray-400">Overall Rating</div>
                <div
                  :class="[
                    'text-xs mt-1 px-2 py-1 rounded-md font-bold border inline-block',
                    getDifficultyColor(saved.osu_star_rating).bg,
                    getDifficultyColor(saved.osu_star_rating).text,
                    getDifficultyColor(saved.osu_star_rating).border,
                  ]"
                >
                  osu!SR: {{ formatOsuSR(saved.osu_star_rating) }}★
                </div>
              </div>
            </div>

            <div class="grid grid-cols-4 md:grid-cols-7 gap-3 text-center">
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-red-400">{{ formatDecimal(saved.stream) }}</div>
                <div class="text-xs text-gray-400">Stream</div>
              </div>
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-orange-400">
                  {{ formatDecimal(saved.jumpstream) }}
                </div>
                <div class="text-xs text-gray-400">Jump</div>
              </div>
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-yellow-400">
                  {{ formatDecimal(saved.handstream) }}
                </div>
                <div class="text-xs text-gray-400">Hand</div>
              </div>
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-green-400">
                  {{ formatDecimal(saved.jackspeed) }}
                </div>
                <div class="text-xs text-gray-400">Jack</div>
              </div>
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-blue-400">
                  {{ formatDecimal(saved.chordjack) }}
                </div>
                <div class="text-xs text-gray-400">Chord</div>
              </div>
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-purple-400">
                  {{ formatDecimal(saved.technical) }}
                </div>
                <div class="text-xs text-gray-400">Tech</div>
              </div>
              <div class="bg-button p-3 rounded-lg">
                <div class="text-lg font-bold text-pink-400">
                  {{ formatDecimal(saved.stamina) }}
                </div>
                <div class="text-xs text-gray-400">Stamina</div>
              </div>
            </div>

            <div class="flex justify-between items-center mt-4 pt-4 border-t border-gray-600">
              <div class="text-xs text-gray-500">
                Analyzed: {{ new Date(saved.analyzed_at).toLocaleString() }}
              </div>
              <div class="text-xs text-gray-500">ID: {{ saved.beatmap_id }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { isAuthenticated } from '@/auth'

const beatmapId = ref<number | null>(null)
const loading = ref(false)
const analyzing = ref(false)
const error = ref<string | null>(null)
const saveSuccess = ref<string | null>(null)
const beatmapset = ref<any>(null)
const selectedDifficulty = ref<any>(null)
const analysis = ref<any>(null)
const selectedRate = ref<string>('1.0') // nm def

const router = useRouter()
const userData = ref<any>(null)
const userLoading = ref(true)

const savedAnalyses = ref<any[]>([])
const showSavedModal = ref(false)

const API_BASE = 'http://localhost:9731'

// rate display
const getRateDisplayName = (rate?: number): string => {
  const rateValue = rate ?? parseFloat(selectedRate.value)
  switch (rateValue) {
    case 0.75:
      return 'HT'
    case 1.0:
      return 'NM'
    case 1.5:
      return 'DT'
    default:
      return `${rateValue}x`
  }
}

const formatDecimal = (val: number | undefined) => {
  if (val === undefined || val === null || Number.isNaN(val)) return 'N/A'
  return val.toFixed(2)
}

const formatOsuSR = (val: number | undefined) => {
  if (val === undefined || val === null || Number.isNaN(val)) return 'N/A'
  return Number(val).toFixed(2)
}

const findStarRatingField = (difficulty: any): number | null => {
  if (!difficulty) return null

  const possibleFields = [
    'difficulty_rating',
    'difficultyrating',
    'star_rating',
    'starrating',
    'difficulty',
    'stars',
    'sr',
  ]

  for (const field of possibleFields) {
    const value = difficulty[field]
    if (typeof value === 'number' && !Number.isNaN(value) && value > 0) {
      return value
    }
  }

  return null
}

// diff colors
const getDifficultyColor = (
  starRating: number | null,
): { bg: string; text: string; border: string } => {
  if (!starRating) return { bg: 'bg-gray-600', text: 'text-white', border: 'border-gray-500' }

  if (starRating < 1) {
    // blue
    return { bg: 'bg-blue-500', text: 'text-white', border: 'border-blue-400' }
  } else if (starRating < 2) {
    // green
    return { bg: 'bg-green-500', text: 'text-white', border: 'border-green-400' }
  } else if (starRating < 3) {
    // yellow
    return { bg: 'bg-yellow-500', text: 'text-black', border: 'border-yellow-400' }
  } else if (starRating < 3.5) {
    // orange
    return { bg: 'bg-orange-500', text: 'text-white', border: 'border-orange-400' }
  } else if (starRating < 4) {
    // red
    return { bg: 'bg-red-500', text: 'text-white', border: 'border-red-400' }
  } else if (starRating < 5) {
    // pink
    return { bg: 'bg-pink-500', text: 'text-white', border: 'border-pink-400' }
  } else if (starRating < 6.5) {
    // purple
    return { bg: 'bg-purple-600', text: 'text-white', border: 'border-purple-500' }
  } else if (starRating < 9) {
    // golden (experience) purple
    return { bg: 'bg-purple-700', text: 'text-yellow-300', border: 'border-purple-600' }
  } else {
    // black
    return { bg: 'bg-gray-900', text: 'text-yellow-300', border: 'border-yellow-400' }
  }
}

// sr to rate
const calculateRateAdjustedSR = (baseSR: number, rate: number): number => {
  if (!baseSR || Number.isNaN(baseSR)) return 0

  // weird ahh formula (close enough)
  const rateMultiplier = Math.pow(rate, 0.8)
  return baseSR * rateMultiplier
}

// sr
const getCurrentStarRating = (): number => {
  if (!selectedDifficulty.value) return 0

  const baseSR = findStarRatingField(selectedDifficulty.value)
  if (!baseSR) return 0

  const rate = parseFloat(selectedRate.value)

  if (rate === 1.0) {
    return baseSR
  }

  return calculateRateAdjustedSR(baseSR, rate)
}

// access token
const getAccessToken = (): string => {
  const token = localStorage.getItem('osu_access_token')
  if (!token) throw new Error('No access token found. Please log in first.')
  return token
}

// saved analysis
const loadSavedAnalyses = () => {
  try {
    const saved = localStorage.getItem('saved_analyses')
    if (saved) {
      savedAnalyses.value = JSON.parse(saved)
    }
  } catch (error) {
    console.error('Error loading saved analyses:', error)
    savedAnalyses.value = []
  }
}

const saveSavedAnalyses = () => {
  try {
    localStorage.setItem('saved_analyses', JSON.stringify(savedAnalyses.value))
  } catch (error) {
    console.error('Error saving analyses:', error)
  }
}

const autoSaveAnalysis = () => {
  if (!analysis.value || !analysis.value.success || !selectedDifficulty.value) {
    return
  }

  const starRating = getCurrentStarRating()

  const dataToSave = {
    beatmap_id: analysis.value.beatmap_id,
    title: analysis.value.title,
    artist: analysis.value.artist,
    difficulty_name: analysis.value.difficulty_name,
    osu_star_rating: starRating,
    our_overall_rating: analysis.value.overall,
    key_count: analysis.value.key_count,
    rate: analysis.value.rate,
    analyzed_at: analysis.value.analyzed_at,
    stream: analysis.value.stream,
    jumpstream: analysis.value.jumpstream,
    handstream: analysis.value.handstream,
    stamina: analysis.value.stamina,
    jackspeed: analysis.value.jackspeed,
    chordjack: analysis.value.chordjack,
    technical: analysis.value.technical,
    hit_objects: analysis.value.hit_objects,
  }

  // analysis existential check (or crisis)
  const exists = savedAnalyses.value.some(
    (saved) =>
      saved.beatmap_id === dataToSave.beatmap_id &&
      saved.difficulty_name === dataToSave.difficulty_name &&
      saved.rate === dataToSave.rate,
  )

  if (exists) {
    saveSuccess.value = 'Analysis already saved previously'
  } else {
    savedAnalyses.value.push(dataToSave)
    saveSavedAnalyses()
    saveSuccess.value = 'Analysis automatically saved!'
  }

  // success clear
  setTimeout(() => {
    saveSuccess.value = null
  }, 3000)
}

const viewSavedAnalyses = () => {
  showSavedModal.value = true
}

const exportAnalyses = () => {
  if (savedAnalyses.value.length === 0) return

  const dataStr = JSON.stringify(savedAnalyses.value, null, 2)
  const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)

  const exportFileDefaultName = `analysis_export_${new Date().toISOString().split('T')[0]}.json`

  const linkElement = document.createElement('a')
  linkElement.setAttribute('href', dataUri)
  linkElement.setAttribute('download', exportFileDefaultName)
  linkElement.click()
}

const clearSavedAnalyses = () => {
  if (confirm('Are you sure you want to clear all saved analyses?')) {
    savedAnalyses.value = []
    saveSavedAnalyses()
  }
}

onMounted(() => {
  if (!isAuthenticated()) {
    router.push('/login')
    return
  }
  loadSavedAnalyses()
  fetchUserData()
})

const fetchUserData = async () => {
  const token = localStorage.getItem('osu_access_token')
  try {
    userLoading.value = true
    const response = await fetch('http://localhost:9831/user', {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error response:', errorText)
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    userData.value = data
  } catch (err) {
    console.error('API Error:', err)
    userData.value = null
  } finally {
    userLoading.value = false
  }
}

// beatmap difficulty loading
const loadDifficulties = async () => {
  if (!beatmapId.value) return

  loading.value = true
  error.value = null
  saveSuccess.value = null
  beatmapset.value = null
  selectedDifficulty.value = null
  analysis.value = null

  try {
    const accessToken = getAccessToken()

    const response = await fetch(`${API_BASE}/list-difficulties`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        beatmap_ids: [beatmapId.value],
        access_token: accessToken,
        osu_session_cookie: localStorage.getItem('osu_session_cookie'),
      }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to load difficulties')
    }

    const data = await response.json()
    if (
      !data ||
      !data.beatmapsets ||
      data.beatmapsets.length === 0 ||
      !data.beatmapsets[0].difficulties ||
      data.beatmapsets[0].difficulties.length === 0
    ) {
      throw new Error('No osu!mania difficulties found in this beatmapset')
    }

    const b = data
    b.artist = b.artist || (b.beatmapsets && b.beatmapsets[0] && b.beatmapsets[0].artist) || ''
    b.title = b.title || (b.beatmapsets && b.beatmapsets[0] && b.beatmapsets[0].title) || ''
    b.creator = b.creator || (b.beatmapsets && b.beatmapsets[0] && b.beatmapsets[0].creator) || ''

    console.log('Full API response:', data)
    console.log('First difficulty:', data.beatmapsets?.[0]?.difficulties?.[0])

    beatmapset.value = b
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error occurred'
  } finally {
    loading.value = false
  }
}

// diff select
const selectDifficulty = (difficulty: any) => {
  selectedDifficulty.value = difficulty
  analysis.value = null
  saveSuccess.value = null
}

// analyze the diff
const analyzeDifficulty = async () => {
  if (!selectedDifficulty.value || !beatmapId.value) return
  analyzing.value = true
  error.value = null
  saveSuccess.value = null

  try {
    const accessToken = getAccessToken()
    const rate = parseFloat(selectedRate.value)

    const response = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        beatmap_ids: [beatmapId.value],
        difficulty_names: [selectedDifficulty.value.difficulty_name],
        access_token: accessToken,
        osu_session_cookie: localStorage.getItem('osu_session_cookie'),
        rate: rate,
      }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Analysis failed')
    }

    const data = await response.json()

    if (!data.results || data.results.length === 0) {
      throw new Error('No analysis results returned')
    }

    const result = data.results[0]
    if (!result.success) {
      throw new Error(result.error_message || 'Analysis failed')
    }

    analysis.value = result

    autoSaveAnalysis()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Analysis failed'
  } finally {
    analyzing.value = false
  }
}

const statsToShow = computed(() => {
  if (!analysis.value) return []
  return [
    { name: 'Stream', value: analysis.value.stream, color: 'text-red-400' },
    { name: 'Jumpstream', value: analysis.value.jumpstream, color: 'text-orange-400' },
    { name: 'Handstream', value: analysis.value.handstream, color: 'text-yellow-400' },
    { name: 'Jackspeed', value: analysis.value.jackspeed, color: 'text-green-400' },
    { name: 'Chordjack', value: analysis.value.chordjack, color: 'text-blue-400' },
    { name: 'Technical', value: analysis.value.technical, color: 'text-purple-400' },
    { name: 'Stamina', value: analysis.value.stamina, color: 'text-pink-400' },
  ]
})

const formattedAnalyzedAt = computed(() => {
  if (!analysis.value || !analysis.value.analyzed_at) return '—'
  try {
    return new Date(analysis.value.analyzed_at).toLocaleString()
  } catch (e) {
    return String(analysis.value.analyzed_at)
  }
})
</script>

<style scoped>
.bg-container {
  background-color: background-container;
}

.bg-analysis {
  background-color: #363636;
}

.bg-button {
  background-color: #474747;
}

.rounded-4xl {
  border-radius: 2rem;
}
</style>
