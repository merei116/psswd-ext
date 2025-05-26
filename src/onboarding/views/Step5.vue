<script setup lang="ts">
import { set } from '../../shared/storage'
import { useRouter } from 'vue-router'

const router = useRouter()

function finish() {
  set({ pg_done: true })         // mark onboarding complete
  window.close()                 // close the popup
}
</script>

<template>
  <section class="card text-center">
    <h2 class="title">All set! 🎉</h2>
    <button @click="$router.push('/analyze')">Перейти в анализатор</button>
  </section>
</template>

<style scoped>
@applyStyles;
</style>
