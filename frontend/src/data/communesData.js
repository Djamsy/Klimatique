// Données complètes des 32 communes de Guadeloupe
export const GUADELOUPE_COMMUNES = [
  // Grande-Terre
  { 
    name: "Pointe-à-Pitre", 
    coordinates: [16.2422, -61.5320], 
    population: "15,410",
    type: "urbaine",
    riskFactors: ["Inondation urbaine", "Cyclones", "Submersion marine"],
    slug: "pointe-a-pitre",
    description: "Principal port et centre économique de la Guadeloupe"
  },
  { 
    name: "Les Abymes", 
    coordinates: [16.2718, -61.5049], 
    population: "58,100",
    type: "urbaine",
    riskFactors: ["Inondation", "Cyclones", "Vents violents"],
    slug: "les-abymes",
    description: "Commune la plus peuplée de Guadeloupe"
  },
  { 
    name: "Baie-Mahault", 
    coordinates: [16.2679, -61.5850], 
    population: "32,400",
    type: "urbaine",
    riskFactors: ["Inondation", "Cyclones", "Zone industrielle"],
    slug: "baie-mahault",
    description: "Zone industrielle et commerciale importante"
  },
  { 
    name: "Le Gosier", 
    coordinates: [16.2024, -61.4935], 
    population: "28,300",
    type: "côtière",
    riskFactors: ["Submersion marine", "Houle cyclonique", "Érosion côtière"],
    slug: "le-gosier",
    description: "Station balnéaire et centre touristique"
  },
  { 
    name: "Sainte-Anne", 
    coordinates: [16.2270, -61.3957], 
    population: "25,400",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Submersion marine", "Sécheresse"],
    slug: "sainte-anne",
    description: "Station balnéaire réputée pour ses plages"
  },
  { 
    name: "Le Moule", 
    coordinates: [16.3304, -61.3496], 
    population: "21,100",
    type: "côtière",
    riskFactors: ["Vents violents", "Houle atlantique", "Érosion côtière"],
    slug: "le-moule",
    description: "Commune côtière exposée aux vents d'est"
  },
  { 
    name: "Saint-François", 
    coordinates: [16.2500, -61.2667], 
    population: "13,900",
    type: "côtière",
    riskFactors: ["Cyclones", "Submersion marine", "Sécheresse"],
    slug: "saint-francois",
    description: "Port de plaisance et centre touristique"
  },
  { 
    name: "Morne-à-l'Eau", 
    coordinates: [16.3320, -61.5288], 
    population: "16,800",
    type: "rurale",
    riskFactors: ["Inondation", "Cyclones", "Submersion marine"],
    slug: "morne-a-l-eau",
    description: "Commune agricole avec zones humides"
  },
  { 
    name: "Petit-Canal", 
    coordinates: [16.4008, -61.5017], 
    population: "7,800",
    type: "rurale",
    riskFactors: ["Inondation fluviale", "Cyclones", "Sécheresse"],
    slug: "petit-canal",
    description: "Commune agricole du nord Grande-Terre"
  },
  { 
    name: "Port-Louis", 
    coordinates: [16.4187, -61.5288], 
    population: "5,500",
    type: "côtière",
    riskFactors: ["Houle", "Vents violents", "Submersion marine"],
    slug: "port-louis",
    description: "Commune côtière du nord-ouest"
  },
  { 
    name: "Anse-Bertrand", 
    coordinates: [16.4708, -61.5029], 
    population: "4,900",
    type: "côtière",
    riskFactors: ["Vents extrêmes", "Houle atlantique", "Sécheresse"],
    slug: "anse-bertrand",
    description: "Pointe nord de la Grande-Terre"
  },

  // Basse-Terre
  { 
    name: "Basse-Terre", 
    coordinates: [15.9959, -61.7261], 
    population: "10,100",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies", "Activité volcanique"],
    slug: "basse-terre",
    description: "Préfecture située au pied de la Soufrière"
  },
  { 
    name: "Petit-Bourg", 
    coordinates: [16.1928, -61.5913], 
    population: "25,500",
    type: "rurale",
    riskFactors: ["Inondation rivières", "Glissements terrain", "Cyclones"],
    slug: "petit-bourg",
    description: "Commune rurale traversée par plusieurs rivières"
  },
  { 
    name: "Lamentin", 
    coordinates: [16.2671, -61.6311], 
    population: "16,100",
    type: "urbaine",
    riskFactors: ["Inondation", "Vents forts", "Submersion"],
    slug: "lamentin",
    description: "Zone aéroportuaire et commerciale"
  },
  { 
    name: "Sainte-Rose", 
    coordinates: [16.3320, -61.6960], 
    population: "19,200",
    type: "côtière",
    riskFactors: ["Cyclones", "Houle", "Glissements terrain"],
    slug: "sainte-rose",
    description: "Commune côtière nord-ouest de Basse-Terre"
  },
  { 
    name: "Capesterre-Belle-Eau", 
    coordinates: [16.0436, -61.5627], 
    population: "18,500",
    type: "montagne",
    riskFactors: ["Cyclones", "Pluies torrentielles", "Coulées boue"],
    slug: "capesterre-belle-eau",
    description: "Commune montagneuse au relief accidenté"
  },
  { 
    name: "Goyave", 
    coordinates: [16.1371, -61.5547], 
    population: "7,700",
    type: "rurale",
    riskFactors: ["Inondation rivières", "Glissements terrain", "Fortes pluies"],
    slug: "goyave",
    description: "Commune agricole en zone de transition"
  },
  { 
    name: "Bouillante", 
    coordinates: [16.1150, -61.7700], 
    population: "7,200",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Vents violents", "Glissements terrain"],
    slug: "bouillante",
    description: "Côte ouest avec centrale géothermique"
  },
  { 
    name: "Deshaies", 
    coordinates: [16.3099, -61.7933], 
    population: "4,100",
    type: "côtière",
    riskFactors: ["Submersion marine", "Cyclones", "Érosion côtière"],
    slug: "deshaies",
    description: "Station balnéaire côte sous le vent"
  },
  { 
    name: "Saint-Claude", 
    coordinates: [16.0254, -61.7081], 
    population: "9,900",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies", "Activité volcanique"],
    slug: "saint-claude",
    description: "Commune d'altitude sur les flancs de la Soufrière"
  },
  { 
    name: "Trois-Rivières", 
    coordinates: [15.9828, -61.6340], 
    population: "8,800",
    type: "côtière",
    riskFactors: ["Submersion marine", "Glissements terrain", "Cyclones"],
    slug: "trois-rivieres",
    description: "Commune côtière sud de Basse-Terre"
  },
  { 
    name: "Vieux-Habitants", 
    coordinates: [16.0894, -61.7758], 
    population: "7,900",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Glissements terrain", "Vents violents"],
    slug: "vieux-habitants",
    description: "Commune côtière ouest avec relief accidenté"
  },
  { 
    name: "Gourbeyre", 
    coordinates: [15.9983, -61.6856], 
    population: "7,500",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Activité volcanique", "Fortes pluies"],
    slug: "gourbeyre",
    description: "Commune de montagne proche de la Soufrière"
  },
  { 
    name: "Vieux-Fort", 
    coordinates: [15.9631, -61.6988], 
    population: "4,100",
    type: "côtière",
    riskFactors: ["Submersion marine", "Glissements terrain", "Cyclones"],
    slug: "vieux-fort",
    description: "Commune la plus au sud de Basse-Terre"
  },
  { 
    name: "Baillif", 
    coordinates: [16.0206, -61.7328], 
    population: "5,200",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Glissements terrain", "Submersion"],
    slug: "baillif",
    description: "Petite commune côtière ouest"
  },

  // Îles du sud
  { 
    name: "Grand-Bourg", 
    coordinates: [15.8837, -61.3119], 
    population: "5,900",
    type: "insulaire",
    riskFactors: ["Isolation", "Submersion marine", "Vents cycloniques"],
    slug: "grand-bourg",
    description: "Chef-lieu de Marie-Galante"
  },
  { 
    name: "Capesterre-de-Marie-Galante", 
    coordinates: [15.8963, -61.2357], 
    population: "3,500",
    type: "insulaire",
    riskFactors: ["Exposition cyclonique", "Submersion marine", "Sécheresse"],
    slug: "capesterre-de-marie-galante",
    description: "Commune de Marie-Galante exposée à l'est"
  },
  { 
    name: "Saint-Louis-de-Marie-Galante", 
    coordinates: [15.9831, -61.3079], 
    population: "2,800",
    type: "insulaire",
    riskFactors: ["Vents violents", "Submersion marine", "Isolement"],
    slug: "saint-louis-de-marie-galante",
    description: "Commune nord de Marie-Galante"
  },
  { 
    name: "La Désirade", 
    coordinates: [16.3147, -61.0749], 
    population: "1,400",
    type: "insulaire",
    riskFactors: ["Isolement extrême", "Vents violents", "Sécheresse"],
    slug: "la-desirade",
    description: "Île la plus orientale de Guadeloupe"
  },
  { 
    name: "Terre-de-Haut", 
    coordinates: [15.8659, -61.5801], 
    population: "1,600",
    type: "insulaire",
    riskFactors: ["Isolement", "Submersion marine", "Vents cycloniques"],
    slug: "terre-de-haut",
    description: "Principale île habitée des Saintes"
  },
  { 
    name: "Terre-de-Bas", 
    coordinates: [15.8569, -61.5669], 
    population: "1,100",
    type: "insulaire",
    riskFactors: ["Isolement critique", "Submersion", "Exposition cyclonique"],
    slug: "terre-de-bas",
    description: "Seconde île habitée des Saintes"
  }
];

// Mapping commune slug vers données complètes
export const COMMUNES_DATA = {};
GUADELOUPE_COMMUNES.forEach(commune => {
  COMMUNES_DATA[commune.slug] = commune;
});

// Communes par type pour statistiques
export const COMMUNES_BY_TYPE = {
  urbaine: GUADELOUPE_COMMUNES.filter(c => c.type === 'urbaine'),
  côtière: GUADELOUPE_COMMUNES.filter(c => c.type === 'côtière'),
  montagne: GUADELOUPE_COMMUNES.filter(c => c.type === 'montagne'),
  rurale: GUADELOUPE_COMMUNES.filter(c => c.type === 'rurale'),
  insulaire: GUADELOUPE_COMMUNES.filter(c => c.type === 'insulaire')
};

export default {
  GUADELOUPE_COMMUNES,
  COMMUNES_DATA,
  COMMUNES_BY_TYPE
};