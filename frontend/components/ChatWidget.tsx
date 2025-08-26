"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { X, Send, MessageCircle, User, Bot, Minimize2, Maximize2, Sparkles, CheckCircle2, Clock, Copy, ThumbsUp, ThumbsDown } from "lucide-react"

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

// Markdown renderer component
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  const renderMarkdown = (text: string) => {
    // Handle bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-black">$1</strong>')
    
    // Handle italic text
    text = text.replace(/\*(.*?)\*/g, '<em class="italic text-black">$1</em>')
    
    // Handle inline code
    text = text.replace(/`(.*?)`/g, '<code class="bg-neutral-200 px-2 py-1 rounded text-sm font-mono text-primary-500">$1</code>')
    
    // Handle links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary-500 hover:text-accent-400 underline" target="_blank" rel="noopener noreferrer">$1</a>')
    
    // Handle line breaks
    text = text.replace(/\n/g, '<br>')
    
    // Handle lists
    text = text.replace(/^- (.+)$/gm, '<li class="ml-4 list-disc text-black">$1</li>')
    text = text.replace(/(<li.*<\/li>)/s, '<ul class="space-y-1 my-2">$1</ul>')
    
    // Handle numbered lists
    text = text.replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal text-black">$1</li>')
    
    return text
  }

  return (
    <div 
      className="prose prose-sm max-w-none text-black leading-relaxed"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  )
}

// Enhanced message bubble component
const MessageBubble: React.FC<{
  message: Message
  onCopy?: (content: string) => void
  onFeedback?: (messageId: string, type: 'like' | 'dislike') => void
}> = ({ message, onCopy, onFeedback }) => {
  const [showActions, setShowActions] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (onCopy) {
      onCopy(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div
      className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-in fade-in-50 slide-in-from-bottom-2 duration-300`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div
        className={`flex items-end space-x-3 max-w-[85%] ${
          message.sender === "user" ? "flex-row-reverse space-x-reverse" : ""
        }`}
      >
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg ${
            message.sender === "user"
              ? "bg-primary-500 text-white"
              : "bg-neutral-200 text-black border border-neutral-300"
          }`}
        >
          {message.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </div>

        <div className="flex flex-col space-y-1">
          <div
            className={`px-4 py-3 rounded-2xl shadow-lg ${
              message.sender === "user"
                ? "bg-primary-500 text-white rounded-br-sm"
                : "bg-white text-black rounded-bl-sm border border-neutral-300"
            }`}
          >
            {message.sender === "assistant" ? (
              <MarkdownRenderer content={message.content} />
            ) : (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            )}
            
            <div className="flex items-center justify-between mt-2">
              <p className={`text-xs ${
                message.sender === "user" ? "text-white/70" : "text-neutral-500"
              }`}>
                {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
              
              {message.sender === "assistant" && showActions && (
                <div className="flex items-center space-x-2 ml-3">
                  <button
                    onClick={handleCopy}
                    className="p-1 hover:bg-neutral-200 rounded transition-colors"
                    title="Copy message"
                  >
                    <Copy className="w-3 h-3 text-neutral-500 hover:text-black" />
                  </button>
                  <button
                    onClick={() => onFeedback?.(message.id, 'like')}
                    className="p-1 hover:bg-neutral-200 rounded transition-colors"
                    title="Good response"
                  >
                    <ThumbsUp className="w-3 h-3 text-neutral-500 hover:text-green-500" />
                  </button>
                  <button
                    onClick={() => onFeedback?.(message.id, 'dislike')}
                    className="p-1 hover:bg-neutral-200 rounded transition-colors"
                    title="Poor response"
                  >
                    <ThumbsDown className="w-3 h-3 text-neutral-500 hover:text-red-500" />
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {copied && (
            <div className="text-xs text-green-500 animate-in fade-in-50">
              Copied to clipboard!
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const ChatWidget: React.FC<ChatWidgetProps> = ({ 
  isOpen, 
  onClose, 
  apiBaseUrl = "https://askairea.com" 
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
        content: "Hello! I'm **AIREA**, your Customer Service AI assistant. Welcome to our real estate company! 🏠✨\n\nWe're here to help you with all your real estate needs. Whether you're looking to buy your dream home or sell your current property, our expert team is ready to assist you.\n\nAre you here today because you're interested in **BUYING** a property or **SELLING** your home?",
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

  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content)
  }

  const handleFeedback = (messageId: string, type: 'like' | 'dislike') => {
    // Here you could send feedback to your analytics service
    console.log(`Feedback for message ${messageId}: ${type}`)
  }

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
        content: "Sorry, I'm having trouble connecting right now. Please try again in a moment.\n\n**Tip:** You can still explore our features while I get back online! 🔄",
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
          content: `✅ **Thank you!** Our agent will contact you shortly to discuss your real estate needs.\n\n*Thank you for choosing AIREA!* 🎉`,
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
      content: "Hello! I'm **AIREA**, your Customer Service AI assistant. Welcome to our real estate company! 🏠✨\n\nWe're here to help you with all your real estate needs. Whether you're looking to buy your dream home or sell your current property, our expert team is ready to assist you.\n\nAre you here today because you're interested in **BUYING** a property or **SELLING** your home?",
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
          <div key={field.key} className="flex items-center justify-between py-2 px-3 bg-neutral-100 rounded-lg border border-neutral-200">
            <div className="flex items-center space-x-2">
              <span className="text-sm">{field.icon}</span>
              <span className="text-black text-sm font-medium">{field.label}:</span>
            </div>
            <span className="text-black text-sm font-semibold">{displayValue}</span>
          </div>
        )
      })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none">
      <div
        className={`bg-white border border-neutral-300 rounded-2xl shadow-2xl pointer-events-auto transition-all duration-300 ${
          isMinimized ? "w-80 h-16" : "w-96 h-[600px]"
        }`}
      >
        {/* Enhanced Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-300 bg-primary-500 text-white rounded-t-2xl">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-lg">
              <Bot className="w-5 h-5 text-primary-500" />
            </div>
            <div>
              <h3 className="font-bold text-white">AIREA Assistant</h3>
              {!isMinimized && (
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${
                    processingData ? "bg-yellow-400 animate-pulse" : 
                    conversationComplete ? "bg-green-400" : "bg-green-400 animate-pulse"
                  }`}></div>
                  <p className="text-xs text-white">
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
            {/* Enhanced Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 h-96 bg-neutral-50 custom-scrollbar">
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onCopy={handleCopyMessage}
                  onFeedback={handleFeedback}
                />
              ))}

              {(isLoading || processingData) && (
                <div className="flex justify-start animate-in fade-in-50">
                  <div className="flex items-end space-x-3">
                    <div className="w-8 h-8 bg-neutral-200 rounded-full flex items-center justify-center border border-neutral-300 shadow-lg">
                      <Bot className="w-4 h-4 text-black" />
                    </div>
                    <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-sm border border-neutral-300 shadow-lg">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-accent-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Enhanced Client Data Summary */}
            {extractedClients.length > 0 && (
              <div className="border-t border-neutral-300 p-4 bg-neutral-100">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-primary-500" />
                    <h4 className="font-semibold text-black text-sm">Lead Information</h4>
                  </div>
                  {conversationComplete ? (
                    <div className="flex items-center space-x-1 px-3 py-1 bg-green-100 text-green-600 text-xs rounded-full border border-green-200">
                      <CheckCircle2 className="w-3 h-3" />
                      <span className="font-medium">Complete</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1 px-3 py-1 bg-blue-100 text-primary-500 text-xs rounded-full border border-blue-200">
                      <Clock className="w-3 h-3" />
                      <span className="font-medium">In Progress</span>
                    </div>
                  )}
                </div>
                <div className="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                  {formatClientData(extractedClients)}
                </div>
              </div>
            )}

            {/* Enhanced Input Area */}
            <div className="border-t border-neutral-300 p-4 bg-white rounded-b-2xl">
              <div className="flex items-center space-x-3">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message..."
                    className="w-full px-4 py-3 pr-12 border border-neutral-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-black placeholder-neutral-400"
                    disabled={isLoading || processingData}
                  />
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    <button
                      onClick={sendMessage}
                      disabled={isLoading || processingData || !inputValue.trim()}
                      className="p-2 bg-primary-500 text-white rounded-lg hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Enhanced Action buttons */}
              <div className="mt-3 flex items-center justify-between">
                {conversationComplete ? (
                  <button
                    onClick={resetConversation}
                    className="text-sm text-primary-500 hover:text-accent-400 transition-colors font-medium flex items-center space-x-1"
                  >
                    <MessageCircle className="w-4 h-4" />
                    <span>Start New Conversation</span>
                  </button>
                ) : (
                  conversationId && messages.length >= 4 && (
                    <button
                      onClick={manualProcessConversation}
                      disabled={processingData}
                      className="text-sm text-green-500 hover:text-green-600 transition-colors font-medium flex items-center space-x-1 disabled:opacity-50"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>{processingData ? "Processing..." : "Process Lead Info"}</span>
                    </button>
                  )
                )}
              </div>

              <div className="mt-2 text-center">
                <p className="text-xs text-neutral-500">
                  Powered by AIREA AI • Press Enter to send • 
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