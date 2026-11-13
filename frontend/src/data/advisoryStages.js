import { FiFileText, FiPieChart, FiShield, FiTrendingUp, FiZap } from 'react-icons/fi'

// Follow-up sessions a returning client can book.
// Stage 1 is the Introduction Meeting (Presentation 1), so this list starts at Stage 2.
export const advisoryStages = [
  {
    id: 'investment-education',
    stage: 2,
    title: 'Investment Education',
    duration: 45,
    icon: FiTrendingUp,
  },
  {
    id: 'tax-education',
    stage: 3,
    title: 'Tax Education',
    duration: 45,
    icon: FiFileText,
  },
  {
    id: 'insurance-education',
    stage: 4,
    title: 'Insurance Education',
    duration: 45,
    icon: FiShield,
  },
  {
    id: 'financial-needs-analysis',
    stage: 5,
    title: 'Financial Needs Analysis (FNA)',
    duration: 60,
    icon: FiPieChart,
  },
  {
    id: 'business-presentation',
    stage: 6,
    title: 'Business Presentation',
    duration: 60,
    icon: FiZap,
  },
  {
    id: 'training-session',
    stage: 7,
    title: 'Training Session',
    duration: 60,
    icon: FiZap,
  },
]
