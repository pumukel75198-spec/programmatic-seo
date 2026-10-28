export interface Alternative {
  name: string;
  description: string;
  pros: string[];
  cons: string[];
  url: string;
}

export interface AlternativeEntry {
  slug: string;
  title: string;
  original: string;
  description: string;
  longDescription: string;
  alternatives: Alternative[];
  tags: string[];
}

export const alternativen: AlternativeEntry[] = [
  {
    slug: 'notion',
    title: 'Notion Alternativen',
    original: 'Notion',
    description:
      'Die besten Notion-Alternativen für Wissensmanagement, Projektplanung und kollaborative Dokumente – von Open Source bis Enterprise.',
    longDescription:
      'Notion hat sich als All-in-One-Workspace etabliert, ist aber nicht für jeden die richtige Wahl. Wer mehr Fokus auf Datenbanken, Offline-Nutzung oder Datenschutz legt, findet in diesen Alternativen starke Optionen. Wir vergleichen Funktionen, Preise und Zielgruppen, damit du die passende Lösung für dein Team findest.',
    alternatives: [
      {
        name: 'Obsidian',
        description: 'Lokale Markdown-Notizen mit mächtigem Plugin-Ökosystem.',
        pros: ['Offline & lokal', 'Sehr schnell', 'Große Plugin-Community'],
        cons: ['Keine native Kollaboration', 'Sync kostenpflichtig'],
        url: 'https://obsidian.md',
      },
      {
        name: 'Coda',
        description: 'Dokumente und Tabellen mit starken Automatisierungen.',
        pros: ['Mächtige Formeln', 'Gute Automatisierung', 'Team-freundlich'],
        cons: ['Lernkurve', 'Preis steigt schnell'],
        url: 'https://coda.io',
      },
      {
        name: 'AppFlowy',
        description: 'Open-Source-Alternative mit Fokus auf Datenschutz.',
        pros: ['Open Source', 'Self-Hosting', 'Notion-ähnliche UI'],
        cons: ['Weniger Integrationen', 'Jüngeres Ökosystem'],
        url: 'https://appflowy.io',
      },
    ],
    tags: ['Produktivität', 'Wissensmanagement', 'Kollaboration'],
  },
  {
    slug: 'zapier',
    title: 'Zapier Alternativen',
    original: 'Zapier',
    description:
      'Zapier-Alternativen für Automatisierung und Integrationen – günstiger, datenschutzfreundlicher oder mit mehr Kontrolle über deine Workflows.',
    longDescription:
      'Zapier ist der Platzhirsch unter den No-Code-Automatisierungstools, doch die Preise und Limits sind für viele Teams eine Hürde. Die folgenden Alternativen bieten teils Self-Hosting, faire Preise oder tiefere Entwickler-Features. Ideal für alle, die Workflows zwischen Apps automatisieren möchten.',
    alternatives: [
      {
        name: 'Make',
        description: 'Visueller Workflow-Builder mit großzügigem Free-Tier.',
        pros: ['Visuelle Szenarien', 'Günstiger als Zapier', 'Viele Integrationen'],
        cons: ['Komplexere UI', 'Operations-Limits'],
        url: 'https://make.com',
      },
      {
        name: 'n8n',
        description: 'Open-Source-Automatisierung mit Self-Hosting-Option.',
        pros: ['Open Source', 'Self-Hosting', 'Code-Nodes'],
        cons: ['Technisches Setup', 'Weniger fertige Templates'],
        url: 'https://n8n.io',
      },
      {
        name: 'Pipedream',
        description: 'Entwicklerfreundliche Plattform mit echtem Code.',
        pros: ['Code-First', 'Gute Developer-Experience', 'Faire Preise'],
        cons: ['Weniger No-Code', 'Kleinere Community'],
        url: 'https://pipedream.com',
      },
    ],
    tags: ['Automatisierung', 'No-Code', 'Integrationen'],
  },
  {
    slug: 'figma',
    title: 'Figma Alternativen',
    original: 'Figma',
    description:
      'Figma-Alternativen für UI-Design und Prototyping – inklusive Open-Source- und datenschutzfreundlicher Optionen.',
    longDescription:
      'Figma dominiert das kollaborative UI-Design, doch Preisanpassungen und Cloud-Zwang bewegen viele Teams zum Umdenken. Diese Alternativen bieten teils lokale Dateien, Self-Hosting oder spezialisierte Workflows für Design-Systeme und Prototyping.',
    alternatives: [
      {
        name: 'Penpot',
        description: 'Open-Source-Design-Tool für Teams, im Browser oder self-hosted.',
        pros: ['Open Source', 'Self-Hosting', 'Web-Standards'],
        cons: ['Weniger Plugins', 'Performance bei großen Dateien'],
        url: 'https://penpot.app',
      },
      {
        name: 'Sketch',
        description: 'Etabliertes macOS-Design-Tool mit lokalem Workflow.',
        pros: ['Native macOS', 'Lokale Dateien', 'Reifes Ökosystem'],
        cons: ['Nur macOS', 'Kollaboration schwächer'],
        url: 'https://www.sketch.com',
      },
      {
        name: 'Framer',
        description: 'Design und Publishing in einem für moderne Websites.',
        pros: ['Direktes Publishing', 'Starke Animationen', 'Schnelles Prototyping'],
        cons: ['Weniger für Design-Systeme', 'Preis pro Site'],
        url: 'https://www.framer.com',
      },
    ],
    tags: ['Design', 'UI/UX', 'Prototyping'],
  },
];
