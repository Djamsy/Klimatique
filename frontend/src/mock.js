// Données mockées pour Météo Sentinelle

export const weatherForecast = [
  {
    id: 1,
    date: "2025-01-15",
    day: "Aujourd'hui",
    temperature: { min: 24, max: 29 },
    weather: "Ensoleillé",
    icon: "sun",
    riskLevel: "faible",
    riskColor: "#22c55e",
    windSpeed: 15,
    precipitation: 0,
    humidity: 65
  },
  {
    id: 2,
    date: "2025-01-16",
    day: "Demain", 
    temperature: { min: 23, max: 28 },
    weather: "Partiellement nuageux",
    icon: "cloud-sun",
    riskLevel: "faible",
    riskColor: "#22c55e",
    windSpeed: 18,
    precipitation: 10,
    humidity: 70
  },
  {
    id: 3,
    date: "2025-01-17",
    day: "Vendredi",
    temperature: { min: 22, max: 27 },
    weather: "Orages possibles",
    icon: "cloud-lightning",
    riskLevel: "modéré",
    riskColor: "#f59e0b",
    windSpeed: 25,
    precipitation: 60,
    humidity: 85
  },
  {
    id: 4,
    date: "2025-01-18",
    day: "Samedi",
    temperature: { min: 21, max: 26 },
    weather: "Fortes pluies",
    icon: "cloud-rain-wind",
    riskLevel: "élevé",
    riskColor: "#f97316",
    windSpeed: 35,
    precipitation: 90,
    humidity: 95
  },
  {
    id: 5,
    date: "2025-01-19",
    day: "Dimanche",
    temperature: { min: 20, max: 25 },
    weather: "Risque cyclonique",
    icon: "tornado",
    riskLevel: "critique",
    riskColor: "#dc2626",
    windSpeed: 60,
    precipitation: 95,
    humidity: 98
  }
];

export const features = [
  {
    id: 1,
    icon: "cloud-sun",
    title: "Prédictions à 5 jours",
    description: "Météo détaillée avec indicateurs de risque spécifiques à chaque commune de Guadeloupe"
  },
  {
    id: 2,
    icon: "bell",
    title: "Alertes en temps réel", 
    description: "Notifications SMS et email automatiques en cas d'événement météorologique extrême"
  },
  {
    id: 3,
    icon: "map",
    title: "Cartes interactives",
    description: "Visualisation en temps réel des vents, précipitations et zones à risque"
  },
  {
    id: 4,
    icon: "database",
    title: "Données locales",
    description: "Croisement météo, topographie et historiques d'impact pour une précision optimale"
  }
];

export const testimonials = [
  {
    id: 1,
    name: "Marie Dubois",
    role: "Maire de Sainte-Anne",
    content: "Grâce à Météo Sentinelle, nous anticipons mieux les risques d'inondation. Un outil indispensable pour protéger nos citoyens.",
    avatar: "MD"
  },
  {
    id: 2,
    name: "Jean-Claude Martin",
    role: "Agriculteur, Basse-Terre",
    content: "Les alertes précises m'ont permis de protéger mes cultures à plusieurs reprises. La précision locale fait toute la différence.",
    avatar: "JM"
  },
  {
    id: 3,
    name: "Dr. Sophie Laurent",
    role: "Médecin urgentiste, CHU",
    content: "L'anticipation des événements extrêmes nous aide à mieux organiser les services d'urgence. Un gain de temps vital.",
    avatar: "SL"
  }
];

export const riskZones = [
  { name: "Pointe-à-Pitre", riskLevel: "modéré", coordinates: [16.2415, -61.5328] },
  { name: "Basse-Terre", riskLevel: "élevé", coordinates: [16.0074, -61.7056] },
  { name: "Sainte-Anne", riskLevel: "faible", coordinates: [16.2276, -61.3825] },
  { name: "Le Moule", riskLevel: "critique", coordinates: [16.3336, -61.3503] }
];

export const stats = [
  { label: "Communes couvertes", value: "32", suffix: "/32" },
  { label: "Précision des alertes", value: "94", suffix: "%" },
  { label: "Temps de réaction", value: "15", suffix: "min" },
  { label: "Utilisateurs actifs", value: "2.5k", suffix: "+" }
];