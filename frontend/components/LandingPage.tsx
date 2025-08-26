"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { useForm } from "react-hook-form"
import {
  MessageCircle,
  TrendingUp,
  Users,
  Phone,
  Mail,
  MapPin,
  Star,
  ArrowRight,
  CheckCircle,
  Shield,
  Home,
  BarChart3,
  Clock,
  Award,
  ChevronRight,
  PlayCircle,
  Sparkles,
  Zap,
  Globe,
  Target,
  Eye,
  Brain,
  Rocket,
  Layers,
  MousePointer,
  Smartphone,
  Calendar,
  DollarSign,
  TrendingDown,
  Activity
} from "lucide-react"

interface ContactFormData {
  name: string
  email: string
  phone: string
  message: string
  lead_type: "buyer" | "seller"
}

interface LandingPageProps {
  onOpenChat: () => void
}

// Modern Stats Counter Component
const AnimatedCounter: React.FC<{ value: number; suffix?: string; prefix?: string }> = ({ 
  value, 
  suffix = "", 
  prefix = "" 
}) => {
  const [count, setCount] = useState(0)
  const [isVisible, setIsVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1 }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (isVisible) {
      const timer = setInterval(() => {
        setCount(prev => {
          if (prev < value) {
            return Math.min(prev + Math.ceil(value / 50), value)
          }
          return value
        })
      }, 50)

      return () => clearInterval(timer)
    }
  }, [isVisible, value])

  return (
    <div ref={ref} className="text-display">
      {prefix}{count.toLocaleString()}{suffix}
    </div>
  )
}

// Feature Card Component
const FeatureCard: React.FC<{
  icon: React.ReactNode
  title: string
  description: string
  bgColor: string
  delay?: number
}> = ({ icon, title, description, bgColor, delay = 0 }) => {
  return (
    <div 
      className="bg-neutral-50 border border-neutral-200 hover:border-primary-500 rounded-2xl p-8 group scroll-reveal shadow-lg hover:shadow-xl transition-all duration-300"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`w-16 h-16 rounded-2xl ${bgColor} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
        {icon}
      </div>
      <h3 className="text-heading text-2xl text-black mb-4">{title}</h3>
      <p className="text-body text-black leading-relaxed mb-6">
        {description}
      </p>
      <div className="flex items-center text-primary-500 font-medium group-hover:text-accent-400 transition-colors">
        <span>Explore feature</span>
        <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
      </div>
    </div>
  )
}

// Modern Process Step Component
const ProcessStep: React.FC<{
  number: number
  title: string
  description: string
  isLast?: boolean
  delay?: number
}> = ({ number, title, description, isLast = false, delay = 0 }) => {
  return (
    <div className="relative scroll-reveal" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-start space-x-6">
        <div className="flex-shrink-0">
          <div className="w-16 h-16 bg-primary-500 rounded-2xl flex items-center justify-center text-white font-bold text-xl shadow-lg">
            {number}
          </div>
        </div>
        <div className="flex-1 pb-8">
          <h3 className="text-heading text-xl text-black mb-3">{title}</h3>
          <p className="text-body text-black">{description}</p>
        </div>
      </div>
      {!isLast && (
        <div className="absolute left-8 top-16 w-0.5 h-16 bg-primary-500 opacity-30"></div>
      )}
    </div>
  )
}

// Enhanced Testimonial Card
const TestimonialCard: React.FC<{
  rating: number
  content: string
  author: string
  location: string
  avatarColor: string
  delay?: number
}> = ({ rating, content, author, location, avatarColor, delay = 0 }) => {
  return (
    <div 
      className="bg-neutral-50 border border-neutral-200 rounded-2xl p-8 scroll-reveal shadow-lg"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center mb-4">
        {[...Array(rating)].map((_, i) => (
          <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
        ))}
      </div>
      <p className="text-body text-black mb-6 leading-relaxed italic">
        "{content}"
      </p>
      <div className="flex items-center space-x-3">
        <div className={`w-12 h-12 rounded-full ${avatarColor} flex items-center justify-center text-white font-bold text-sm`}>
          {author.split(' ').map(n => n[0]).join('')}
        </div>
        <div>
          <div className="font-semibold text-black">{author}</div>
          <div className="text-neutral-600 text-sm">{location}</div>
        </div>
      </div>
    </div>
  )
}

const LandingPage: React.FC<LandingPageProps> = ({ onOpenChat }) => {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ContactFormData>()

  // Scroll reveal animation
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed')
          }
        })
      },
      { threshold: 0.1 }
    )

    const elements = document.querySelectorAll('.scroll-reveal')
    elements.forEach((el) => observer.observe(el))

    return () => observer.disconnect()
  }, [])

  const onSubmit = async (data: ContactFormData) => {
    setIsSubmitting(true)
    try {
      await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })
      setSubmitSuccess(true)
      reset()
      setTimeout(() => setSubmitSuccess(false), 5000)
    } catch (error) {
      console.error("Error submitting form:", error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-neutral-200 border-b border-secondary-900/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
                <Home className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-display text-black">
                AIREA
              </span>
            </div>
            
            <div className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-black hover:text-primary-500 font-medium transition-colors">
                Features
              </a>
              <a href="#how-it-works" className="text-black hover:text-primary-500 font-medium transition-colors">
                How It Works
              </a>
              <a href="#testimonials" className="text-black hover:text-primary-500 font-medium transition-colors">
                Reviews
              </a>
              <a href="#contact" className="text-black hover:text-primary-500 font-medium transition-colors">
                Contact
              </a>
              <button
                onClick={onOpenChat}
                className="btn-modern bg-primary-500 text-white px-6 py-2.5 rounded-full hover:shadow-lg transition-all duration-200 flex items-center space-x-2"
              >
                <MessageCircle className="w-4 h-4" />
                <span>Start Chat</span>
              </button>
            </div>

            <div className="md:hidden">
              <button className="text-black">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-24 pb-20 bg-white min-h-screen flex items-center">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="animate-slide-up">
              <div className="inline-flex items-center px-4 py-2 rounded-full bg-accent-400/10 border border-accent-400/30 mb-8">
                <Sparkles className="w-4 h-4 text-accent-400 mr-2" />
                <span className="text-primary-500 font-medium text-sm">AI-Powered Real Estate Revolution</span>
              </div>
              
              <h1 className="text-display text-6xl lg:text-7xl font-bold text-black leading-tight mb-8">
                Find Your
                <span className="text-primary-500 block">
                  Dream Home
                </span>
                With AI Magic
              </h1>
              
              <p className="text-body text-xl text-black mb-10 leading-relaxed max-w-lg">
                Experience the future of real estate with instant property valuations, smart recommendations, 
                and 24/7 AI assistance that understands your needs.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 mb-12">
                <button
                  onClick={onOpenChat}
                  className="btn-modern bg-primary-500 text-white px-8 py-4 rounded-full font-semibold hover:shadow-xl transition-all duration-200 flex items-center justify-center space-x-2 text-lg"
                >
                  <MessageCircle className="w-5 h-5" />
                  <span>Start AI Chat</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
              
              </div>
              
              <div className="flex items-center space-x-8">
                <div className="flex items-center space-x-2">
                  <div className="flex -space-x-2">
                    <div className="w-8 h-8 rounded-full bg-primary-500 border-2 border-white"></div>
                    <div className="w-8 h-8 rounded-full bg-accent-400 border-2 border-white"></div>
                    <div className="w-8 h-8 rounded-full bg-secondary-900 border-2 border-white"></div>
                  </div>
                  <span className="text-black font-medium">25,000+ Users</span>
                </div>
                <div className="flex items-center space-x-1">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  ))}
                  <span className="text-black font-medium ml-2">4.9/5</span>
                </div>
              </div>
            </div>
            
            <div className="relative lg:block hidden animate-slide-right">
              {/* Floating Elements */}
              <div className="absolute inset-0 z-10">
                <div className="absolute top-8 -left-6 bg-neutral-50 border border-green-400/30 rounded-2xl p-4 floating-element shadow-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-14 h-14 bg-green-500 rounded-xl flex items-center justify-center">
                      <TrendingUp className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <div className="font-bold text-black text-lg">$1.2M</div>
                      <div className="text-sm text-neutral-600 font-medium">Property Value</div>
                      <div className="text-xs text-green-500 font-semibold">↗ +22% this year</div>
                    </div>
                  </div>
                </div>
                
                <div className="absolute bottom-8 -right-6 bg-neutral-50 border border-blue-400/30 rounded-2xl p-4 floating-element shadow-lg" style={{ animationDelay: '1s' }}>
                  <div className="flex items-center space-x-3">
                    <div className="w-14 h-14 bg-primary-500 rounded-xl flex items-center justify-center">
                      <Brain className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <div className="font-bold text-black text-lg">AI Ready</div>
                      <div className="text-sm text-neutral-600 font-medium">24/7 Available</div>
                      <div className="flex items-center space-x-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <div className="text-xs text-green-500 font-semibold">Online Now</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="absolute top-1/3 right-4 bg-neutral-50 border border-purple-400/30 rounded-xl p-3 floating-element shadow-lg" style={{ animationDelay: '2s' }}>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary-500">99.2%</div>
                    <div className="text-xs text-neutral-600 font-medium">Accuracy Rate</div>
                  </div>
                </div>
              </div>

              {/* Main Image */}
              <div className="relative bg-neutral-50 border border-neutral-200 rounded-3xl p-6 transform hover:scale-105 transition-all duration-500 shadow-lg">
                <div className="absolute -top-3 left-6 bg-yellow-400 text-black px-4 py-2 rounded-full text-sm font-bold shadow-lg z-10">
                  ⭐ Premium Agent
                </div>
                
                <div className="relative overflow-hidden rounded-2xl">
                  <img
                    src="/Adobe Express - file.png"
                    alt="Beautiful professional woman portrait, elegant business attire, confident pose, premium corporate photography, real estate professional by TRAN NHU TUAN on Unsplash"
                    className="w-full h-auto object-cover transform hover:scale-110 transition-transform duration-700"
                    style={{ maxHeight: "500px", minHeight: "400px", width: "100%", height: "50%" }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Enhanced Stats Section */}
      <section className="py-20 relative bg-neutral-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="text-center bg-white rounded-2xl p-8 scroll-reveal border border-neutral-200 shadow-lg">
              <div className="text-5xl font-bold text-primary-500 mb-2">
                <AnimatedCounter value={75} suffix="K+" />
              </div>
              <div className="text-black text-lg">Properties Analyzed</div>
            </div>
            <div className="text-center bg-white rounded-2xl p-8 scroll-reveal border border-neutral-200 shadow-lg" style={{ animationDelay: '100ms' }}>
              <div className="text-5xl font-bold text-primary-500 mb-2">
                <AnimatedCounter value={99.2} suffix="%" />
              </div>
              <div className="text-black text-lg">Accuracy Rate</div>
            </div>
            <div className="text-center bg-white rounded-2xl p-8 scroll-reveal border border-neutral-200 shadow-lg" style={{ animationDelay: '200ms' }}>
              <div className="text-5xl font-bold text-primary-500 mb-2">24/7</div>
              <div className="text-black text-lg">AI Availability</div>
            </div>
            <div className="text-center bg-white rounded-2xl p-8 scroll-reveal border border-neutral-200 shadow-lg" style={{ animationDelay: '300ms' }}>
              <div className="text-5xl font-bold text-primary-500 mb-2">
                <AnimatedCounter value={25} suffix="K+" />
              </div>
              <div className="text-black text-lg">Happy Clients</div>
            </div>
          </div>
        </div>
      </section>

      {/* Revolutionary Features Section */}
      <section id="features" className="py-20 relative bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 scroll-reveal">
            <h2 className="text-display text-5xl font-bold text-black mb-6">
              Revolutionary AI Technology
            </h2>
            <p className="text-body text-xl text-black max-w-3xl mx-auto">
              Our cutting-edge artificial intelligence delivers unprecedented accuracy and insights 
              for all your real estate needs, powered by advanced machine learning algorithms.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={<BarChart3 className="w-8 h-8 text-white" />}
              title="Instant AI Valuations"
              description="Get precise property valuations in seconds using our advanced neural networks and comprehensive market data analysis with 99.2% accuracy."
              bgColor="bg-blue-500"
              delay={0}
            />

            <FeatureCard
              icon={<Brain className="w-8 h-8 text-white" />}
              title="Smart AI Assistant"
              description="Our intelligent chatbot provides personalized recommendations and answers your questions 24/7 with human-like understanding and empathy."
              bgColor="bg-green-500"
              delay={100}
            />

            <FeatureCard
              icon={<Target className="w-8 h-8 text-white" />}
              title="Perfect Matches"
              description="Connect with top-rated agents and find properties that match your exact criteria using our intelligent matching system and predictive analytics."
              bgColor="bg-purple-500"
              delay={200}
            />

            <FeatureCard
              icon={<Eye className="w-8 h-8 text-white" />}
              title="Market Insights"
              description="Access real-time market trends, neighborhood analytics, and investment opportunities powered by big data and machine learning."
              bgColor="bg-orange-500"
              delay={300}
            />

            <FeatureCard
              icon={<Rocket className="w-8 h-8 text-white" />}
              title="Instant Processing"
              description="Lightning-fast document processing, mortgage pre-approval, and transaction management with automated workflows."
              bgColor="bg-cyan-500"
              delay={400}
            />

            <FeatureCard
              icon={<Shield className="w-8 h-8 text-white" />}
              title="Secure & Private"
              description="Bank-level security with end-to-end encryption, ensuring your personal and financial information is always protected."
              bgColor="bg-teal-500"
              delay={500}
            />
          </div>
        </div>
      </section>

      {/* Interactive Process Timeline */}
      <section id="how-it-works" className="py-20 relative bg-neutral-100">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 scroll-reveal">
            <h2 className="text-display text-5xl font-bold text-black mb-6">
              How AIREA Works
            </h2>
            <p className="text-body text-xl text-black max-w-3xl mx-auto">
              Our streamlined AI-powered process makes buying or selling real estate 
              simple, fast, and incredibly efficient.
            </p>
          </div>

          <div className="space-y-8">
            <ProcessStep
              number={1}
              title="Start AI Conversation"
              description="Begin chatting with our advanced AI assistant about your real estate needs, preferences, and goals. Our AI learns and adapts to your unique requirements."
              delay={0}
            />

            <ProcessStep
              number={2}
              title="Get Instant Analysis"
              description="Receive immediate property valuations, comprehensive market insights, and personalized recommendations powered by our machine learning algorithms."
              delay={100}
            />

            <ProcessStep
              number={3}
              title="Smart Matching & Tours"
              description="Get matched with expert agents and properties that perfectly fit your criteria. Schedule virtual or in-person tours with our intelligent scheduling system."
              delay={200}
            />

            <ProcessStep
              number={4}
              title="Close Successfully"
              description="Complete your transaction with confidence, backed by AI-powered market insights, automated paperwork, and continuous support throughout the process."
              isLast={true}
              delay={300}
            />
          </div>
        </div>
      </section>

      {/* Enhanced Testimonials */}
      <section id="testimonials" className="py-20 relative bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 scroll-reveal">
            <h2 className="text-display text-5xl font-bold text-black mb-6">
              What Our Clients Say
            </h2>
            <p className="text-body text-xl text-black">
              Real stories from real people who transformed their real estate experience with AIREA
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <TestimonialCard
              rating={5}
              content="The AI assistant helped me get an accurate valuation instantly. I sold my house 25% above my expected price thanks to the incredible market insights and timing recommendations!"
              author="Sarah Johnson"
              location="Salt Lake City, UT"
              avatarColor="bg-blue-500"
              delay={0}
            />

            <TestimonialCard
              rating={5}
              content="Found my dream home in just 10 days! The AI understood exactly what I was looking for and connected me with the perfect agent. The whole process was seamless and stress-free."
              author="Mike Rodriguez"
              location="Provo, UT"
              avatarColor="bg-green-500"
              delay={100}
            />

            <TestimonialCard
              rating={5}
              content="The 24/7 availability was a game-changer. Got answers to all my questions at 2 AM and scheduled a showing for the next morning. The AI is incredibly smart and helpful!"
              author="Emily Chen"
              location="Park City, UT"
              avatarColor="bg-purple-500"
              delay={200}
            />
          </div>
        </div>
      </section>

      {/* Modern Contact Section */}
      <section id="contact" className="py-20 relative bg-neutral-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="scroll-reveal">
              <h2 className="text-display text-5xl font-bold text-black mb-8">
                Ready to Get Started?
              </h2>
              <p className="text-body text-xl text-black mb-10">
                Whether you're buying or selling, our AI assistant is here to help you every step of the way. 
                Start your journey to finding your dream home today.
              </p>

              <div className="space-y-6 mb-10">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-primary-500 rounded-xl flex items-center justify-center">
                    <Phone className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-black text-lg">(555) 123-4567</div>
                    <div className="text-neutral-600">Available 24/7 with AI support</div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center">
                    <Mail className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-black text-lg">info@askairea.com</div>
                    <div className="text-neutral-600">Instant AI-powered responses</div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-purple-500 rounded-xl flex items-center justify-center">
                    <MapPin className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-black text-lg">Salt Lake City, UT</div>
                    <div className="text-neutral-600">Serving all of Utah and beyond</div>
                  </div>
                </div>
              </div>

              <button
                onClick={onOpenChat}
                className="btn-modern bg-primary-500 text-white px-8 py-4 rounded-full font-semibold hover:shadow-xl transition-all duration-200 flex items-center space-x-2 text-lg"
              >
                <MessageCircle className="w-5 h-5" />
                <span>Start AI Conversation</span>
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-white border border-neutral-200 rounded-3xl p-8 scroll-reveal shadow-lg">
              <h3 className="text-heading text-3xl font-bold text-black mb-8">Get In Touch</h3>

              {submitSuccess && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="font-medium text-green-700">Message sent successfully!</span>
                  </div>
                  <p className="mt-1 text-green-600">We'll contact you within 24 hours.</p>
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-black mb-2">Name</label>
                  <input
                    {...register("name", { required: "Name is required" })}
                    className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-black placeholder-neutral-400"
                    placeholder="Your full name"
                  />
                  {errors.name && (
                    <p className="text-sm mt-1 text-red-500">{errors.name.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-black mb-2">Email</label>
                  <input
                    {...register("email", {
                      required: "Email is required",
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: "Invalid email address",
                      },
                    })}
                    type="email"
                    className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-black placeholder-neutral-400"
                    placeholder="your@email.com"
                  />
                  {errors.email && (
                    <p className="text-sm mt-1 text-red-500">{errors.email.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-black mb-2">Phone</label>
                  <input
                    {...register("phone", { required: "Phone is required" })}
                    type="tel"
                    className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-black placeholder-neutral-400"
                    placeholder="(555) 123-4567"
                  />
                  {errors.phone && (
                    <p className="text-sm mt-1 text-red-500">{errors.phone.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-black mb-2">I'm interested in</label>
                  <select
                    {...register("lead_type", { required: "Please select an option" })}
                    className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-black"
                  >
                    <option value="" className="bg-white">Select...</option>
                    <option value="buyer" className="bg-white">Buying a property</option>
                    <option value="seller" className="bg-white">Selling a property</option>
                  </select>
                  {errors.lead_type && (
                    <p className="text-sm mt-1 text-red-500">{errors.lead_type.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-black mb-2">Message</label>
                  <textarea
                    {...register("message", { required: "Message is required" })}
                    rows={4}
                    className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-black placeholder-neutral-400"
                    placeholder="Tell us about your real estate needs..."
                  />
                  {errors.message && (
                    <p className="text-sm mt-1 text-red-500">{errors.message.message}</p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full btn-modern bg-primary-500 text-white py-3 px-6 rounded-lg font-semibold hover:shadow-lg transition-all duration-200 disabled:opacity-50"
                >
                  {isSubmitting ? "Sending..." : "Send Message"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-500 relative">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="scroll-reveal">
            <h2 className="text-display text-5xl font-bold mb-8 text-white">
              Experience the Future of Real Estate Today
            </h2>
            <p className="text-body text-xl mb-10 text-white">
              Join thousands of satisfied customers who have transformed their real estate experience 
              with our revolutionary AI technology. Your dream home is just a conversation away.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={onOpenChat}
                className="btn-modern bg-white text-primary-500 px-8 py-4 rounded-full font-semibold text-lg hover:shadow-xl transition-all duration-200 inline-flex items-center space-x-2"
              >
                <MessageCircle className="w-5 h-5" />
                <span>Start Your AI-Powered Journey</span>
                <ArrowRight className="w-5 h-5" />
              </button>
              
              <button className="btn-modern bg-transparent border-2 border-white text-white px-8 py-4 rounded-full font-semibold text-lg hover:bg-white hover:text-primary-500 transition-all duration-200 inline-flex items-center space-x-2">
                <PlayCircle className="w-5 h-5" />
                <span>Watch Success Stories</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Modern Footer */}
      <footer className="py-16 bg-neutral-200 border-t border-secondary-900/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
                  <Home className="w-6 h-6 text-white" />
                </div>
                <span className="text-2xl font-bold text-display text-black">AIREA</span>
              </div>
              <p className="text-neutral-600 leading-relaxed">
                Revolutionizing real estate with AI-powered solutions for buyers, sellers, and agents worldwide. 
                The future of property is here.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-4 text-black">AI Services</h3>
              <ul className="space-y-2 text-neutral-600">
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Smart Valuations</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">AI Assistant</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Agent Matching</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Market Analytics</li>
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-4 text-black">Company</h3>
              <ul className="space-y-2 text-neutral-600">
                <li className="hover:text-primary-500 transition-colors cursor-pointer">About AIREA</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Careers</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Press Kit</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Contact</li>
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-4 text-black">Support</h3>
              <ul className="space-y-2 text-neutral-600">
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Help Center</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Privacy Policy</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Terms of Service</li>
                <li className="hover:text-primary-500 transition-colors cursor-pointer">Cookie Policy</li>
              </ul>
            </div>
          </div>

          <div className="border-t border-neutral-300 pt-8 text-center text-neutral-600">
            <p>&copy; 2024 AIREA. All rights reserved. Built with AI for the future of real estate.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage