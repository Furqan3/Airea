"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { X, Send, MessageCircle, User, Bot, Minimize2, Maximize2, Sparkles, CheckCircle2, Clock } from "lucide-react"

interface Message {
  id: string
  content: string
  sender: "user" | "assistant"
  timestamp: Date
}

interface Client {
  client_type: "Buyer" | "Seller"
  name: string
  phone: string
  email: string
  property_type?: "House" | "Apartment" | "Condo" | "Townhouse"
  address?: string
  budget?: number
  appointment?: boolean
  appointment_time?: string
  details?: string
}

interface ChatResponse {
  message: string
  conversation_id: string
  clients_processed?: number
}

interface ProcessDataResponse {
  clients_extracted: number
  clients_processed: number
  success: boolean
  errors?: string[]
}

interface ChatWidgetProps {
  isOpen: boolean
  onClose: () => void
  apiBaseUrl?: string
}

const ChatWidget: React.FC<ChatWidgetProps> = ({ 
  isOpen, 
  onClose, 
  apiBaseUrl = "http://localhost:8000" 
}) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [extractedClients, setExtractedClients] = useState<Client[]>([])
  const [isMinimized, setIsMinimized] = useState(false)
  const [conversationComplete, setConversationComplete] = useState(false)
  const [processingData, setProcessingData] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const initialMessage: Message = {
        id: Date.now().toString(),
        content: "Hi! I'm AIREA, your AI real estate assistant. 🏠✨\n\nI'm here to help whether you're buying, selling, or just exploring the market. What brings you here today?",
        sender: "assistant",
        timestamp: new Date(),
      }
      setMessages([initialMessage])
    }
  }, [isOpen])

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen, isMinimized])

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsLoading(true)

    try {
            const response = await fetch(`${apiBaseUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: inputValue,
          conversation_id: conversationId,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ChatResponse = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.message,
        sender: "assistant",
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
      setConversationId(data.conversation_id)

      // Check if we should process the conversation (after several exchanges)
      const totalMessages = messages.length + 2 // +2 for current user and assistant messages
      if (totalMessages >= 6 && !conversationComplete) {
        await processConversation(data.conversation_id)
      }

    } catch (error) {
      console.error("Error sending message:", error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "Sorry, I'm having trouble connecting right now. Please try again in a moment.",
        sender: "assistant",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const processConversation = async (convId?: string) => {
    if (!convId && !conversationId) return

    setProcessingData(true)
    try {
            const response = await fetch(`${apiBaseUrl}/api/process-conversation/${convId || conversationId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ProcessDataResponse = await response.json()

      if (data.success && data.clients_extracted > 0) {
        setConversationComplete(true)
        
        // Fetch the updated clients list
        await fetchClients()

        // Show success message
        const successMessage: Message = {
          id: (Date.now() + 2).toString(),
          content: `✅ Great! I've captured your information successfully. ${data.clients_processed} lead(s) have been processed and our team will be in touch with you shortly!`,
          sender: "assistant",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, successMessage])
      }

    } catch (error) {
      console.error("Error processing conversation:", error)
    } finally {
      setProcessingData(false)
    }
  }

  const fetchClients = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/clients`)
      if (response.ok) {
        const data = await response.json()
        setExtractedClients(data.clients || [])
      }
    } catch (error) {
      console.error("Error fetching clients:", error)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const resetConversation = () => {
    setMessages([])
    setExtractedClients([])
    setConversationId(null)
    setConversationComplete(false)
    setProcessingData(false)

    const initialMessage: Message = {
      id: Date.now().toString(),
      content: "Hi! I'm AIREA, your AI real estate assistant. 🏠✨\n\nI'm here to help whether you're buying, selling, or just exploring the market. What brings you here today?",
      sender: "assistant",
      timestamp: new Date(),
    }
    setMessages([initialMessage])
  }

  const manualProcessConversation = async () => {
    if (conversationId) {
      await processConversation()
    }
  }

  const formatClientData = (clients: Client[]) => {
    if (clients.length === 0) return null

    const latestClient = clients[clients.length - 1] // Get the most recent client

    const fields = [
      { key: "name", label: "Name", icon: "👤" },
      { key: "email", label: "Email", icon: "📧" },
      { key: "phone", label: "Phone", icon: "📱" },
      { key: "client_type", label: "Type", icon: "🏠" },
      { key: "address", label: "Address", icon: "📍" },
      { key: "property_type", label: "Property Type", icon: "🏢" },
      { key: "budget", label: "Budget", icon: "💰", format: (value: any) => value ? `$${Number(value).toLocaleString()}` : null },
    ]

    return fields
      .filter((field) => {
        const value = latestClient[field.key as keyof Client]
        return value && String(value).trim()
      })
      .map((field) => {
        const value = latestClient[field.key as keyof Client]
        const displayValue = field.format ? field.format(value) : String(value)
        
        return (
          <div key={field.key} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <span className="text-sm">{field.icon}</span>
              <span className="text-gray-600 text-sm font-medium">{field.label}:</span>
            </div>
            <span className="text-gray-900 text-sm font-semibold">{displayValue}</span>
          </div>
        )
      })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none">
      <div
        className={`bg-white border border-gray-200 rounded-2xl shadow-2xl pointer-events-auto transition-all duration-300 ${
          isMinimized ? "w-80 h-16" : "w-96 h-[600px]"
        }`}
        style={{
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-2xl">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm border border-white/30">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white">AIREA Assistant</h3>
              {!isMinimized && (
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${
                    processingData ? "bg-yellow-400 animate-pulse" : 
                    conversationComplete ? "bg-green-400" : "bg-green-400 animate-pulse"
                  }`}></div>
                  <p className="text-xs text-blue-100">
                    {processingData ? "Processing your information..." :
                     conversationComplete ? "Lead captured successfully!" : 
                     "Online • Ready to help"}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-2 hover:bg-white/20 rounded-xl transition-colors text-white"
            >
              {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
            </button>
            <button 
              onClick={onClose} 
              className="p-2 hover:bg-white/20 rounded-xl transition-colors text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 h-96 bg-gradient-to-b from-gray-50/50 to-white">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-in fade-in-50 slide-in-from-bottom-2 duration-300`}
                >
                  <div
                    className={`flex items-end space-x-2 max-w-[85%] ${
                      message.sender === "user" ? "flex-row-reverse space-x-reverse" : ""
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${
                        message.sender === "user"
                          ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
                          : "bg-gradient-to-r from-gray-100 to-gray-200 text-gray-600 border border-gray-200"
                      }`}
                    >
                      {message.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    <div
                      className={`px-4 py-3 rounded-2xl shadow-sm ${
                        message.sender === "user"
                          ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-sm"
                          : "bg-white text-gray-800 rounded-bl-sm border border-gray-100"
                      }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                      <p className={`text-xs mt-2 ${
                        message.sender === "user" ? "text-blue-100" : "text-gray-500"
                      }`}>
                        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {(isLoading || processingData) && (
                <div className="flex justify-start animate-in fade-in-50">
                  <div className="flex items-end space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-r from-gray-100 to-gray-200 rounded-full flex items-center justify-center border border-gray-200">
                      <Bot className="w-4 h-4 text-gray-600" />
                    </div>
                    <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-sm border border-gray-100 shadow-sm">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Client Data Summary */}
            {extractedClients.length > 0 && (
              <div className="border-t border-gray-100 p-4 bg-gray-50">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-blue-600" />
                    <h4 className="font-semibold text-gray-900 text-sm">Lead Information</h4>
                  </div>
                  {conversationComplete ? (
                    <div className="flex items-center space-x-1 px-3 py-1 bg-green-100 text-green-700 text-xs rounded-full border border-green-200">
                      <CheckCircle2 className="w-3 h-3" />
                      <span className="font-medium">Complete</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1 px-3 py-1 bg-blue-100 text-blue-700 text-xs rounded-full border border-blue-200">
                      <Clock className="w-3 h-3" />
                      <span className="font-medium">In Progress</span>
                    </div>
                  )}
                </div>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {formatClientData(extractedClients)}
                </div>
              </div>
            )}

            {/* Input Area */}
            <div className="border-t border-gray-100 p-4 bg-white rounded-b-2xl">
              <div className="flex items-center space-x-3">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message..."
                    className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50 text-gray-900 placeholder-gray-500"
                    disabled={isLoading || processingData}
                  />
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    <button
                      onClick={sendMessage}
                      disabled={isLoading || processingData || !inputValue.trim()}
                      className="p-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-3 flex items-center justify-between">
                {conversationComplete ? (
                  <button
                    onClick={resetConversation}
                    className="text-sm text-blue-600 hover:text-blue-700 transition-colors font-medium flex items-center space-x-1"
                  >
                    <MessageCircle className="w-4 h-4" />
                    <span>Start New Conversation</span>
                  </button>
                ) : (
                  conversationId && messages.length >= 4 && (
                    <button
                      onClick={manualProcessConversation}
                      disabled={processingData}
                      className="text-sm text-green-600 hover:text-green-700 transition-colors font-medium flex items-center space-x-1 disabled:opacity-50"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>{processingData ? "Processing..." : "Process Lead Info"}</span>
                    </button>
                  )
                )}
              </div>

              <div className="mt-2 text-center">
                <p className="text-xs text-gray-400">
                  Powered by AIREA AI • Press Enter to send
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default ChatWidget