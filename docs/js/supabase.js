// docs/js/supabase.js
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

export const supabase = createClient(
  'https://klfoqpkffnkivcrfgmta.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtsZm9xcGtmZm5raXZjcmZnbXRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY3MDYyNDEsImV4cCI6MjA2MjI4MjI0MX0.Bchuea3eYQetqHcJDaBCJiigU1L_9ULjceKFs_ZCWWU'
)