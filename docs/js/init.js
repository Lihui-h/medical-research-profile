import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
		  
// 初始化配置
const supabaseUrl = 'https://klfoqpkffnkivcrfgmta.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtsZm9xcGtmZm5raXZjcmZnbXRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY3MDYyNDEsImV4cCI6MjA2MjI4MjI0MX0.Bchuea3eYQetqHcJDaBCJiigU1L_9ULjceKFs_ZCWWU'

// 创建客户端实例
const supabase = createClient(supabaseUrl, supabaseKey)

// 暴露到全局对象
window.supabase = supabase

// 🎯 会话监控代码放在这里
supabase.auth.onAuthStateChange((event, session) => {
    console.log(`认证状态变更: ${event}`, session)
    
    if (event === 'SIGNED_OUT') {
    window.location.reload()
    }
    
    if (event === 'TOKEN_REFRESHED') {
    console.log('会话令牌已更新')
    }
})