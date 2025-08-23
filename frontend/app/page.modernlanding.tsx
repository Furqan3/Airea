'use client'

import { useState } from 'react'
import LandingPage from '@/components/LandingPage'
import ChatWidget from '@/components/ChatWidget'

export default function ModernLandingPreview() {
  const [isChatOpen, setIsChatOpen] = useState(false)

  return (
    <main className="min-h-screen">
      <LandingPage onOpenChat={() => setIsChatOpen(true)} />
      <ChatWidget
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
      />
    </main>
  )
}