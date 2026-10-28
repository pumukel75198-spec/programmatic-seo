export interface WorkflowStep {
  title: string;
  description: string;
}

export interface WorkflowEntry {
  slug: string;
  title: string;
  description: string;
  longDescription: string;
  difficulty: 'Einsteiger' | 'Fortgeschritten' | 'Experte';
  duration: string;
  tools: string[];
  steps: WorkflowStep[];
  tags: string[];
}

export const workflows: WorkflowEntry[] = [
  {
    slug: 'content-automation',
    title: 'Content-Automation mit KI',
    description:
      'Ein vollständiger Workflow, um mit KI und APIs Content-Ideen zu recherchieren, zu schreiben und automatisiert zu veröffentlichen.',
    longDescription:
      'Dieser Workflow zeigt, wie du einen skalierbaren Content-Prozess aufbaust: von der Keyword-Recherche über die KI-gestützte Texterstellung bis zur automatischen Veröffentlichung. Ideal für Programmatic-SEO-Projekte, bei denen hunderte Seiten effizient entstehen sollen.',
    difficulty: 'Fortgeschritten',
    duration: 'ca. 2–3 Stunden Setup',
    tools: ['OpenAI API', 'Supabase', 'Astro', 'n8n'],
    steps: [
      {
        title: 'Keyword- und Themenrecherche',
        description:
          'Sammle Suchbegriffe und clustere sie nach Intent. Nutze APIs oder CSV-Importe, um eine strukturierte Themenliste zu erzeugen.',
      },
      {
        title: 'Datenmodell anlegen',
        description:
          'Speichere Themen, Status und Metadaten in einer Datenbank wie Supabase, damit der Workflow zustandsbehaftet arbeitet.',
      },
      {
        title: 'KI-Texterstellung',
        description:
          'Erzeuge über die OpenAI API Entwürfe mit klaren Prompts und strukturierten Ausgaben (JSON), inklusive Meta-Beschreibung.',
      },
      {
        title: 'Qualitätssicherung',
        description:
          'Prüfe Fakten, Duplikate und SEO-Kriterien automatisiert und markiere Seiten zur manuellen Freigabe.',
      },
      {
        title: 'Automatische Veröffentlichung',
        description:
          'Baue die Seiten mit Astro als statische Routen und deploye sie per CI/CD bei jeder Freigabe.',
      },
    ],
    tags: ['KI', 'Content', 'SEO', 'Automatisierung'],
  },
  {
    slug: 'lead-qualification',
    title: 'Lead-Qualifizierung automatisieren',
    description:
      'Eingehende Leads automatisch bewerten, anreichern und an das richtige Team weiterleiten – ohne manuelle Sortierung.',
    longDescription:
      'Manuelle Lead-Qualifizierung kostet Zeit und führt zu Verzögerungen. Dieser Workflow verbindet Formulare, CRM und KI, um Leads in Echtzeit zu bewerten, mit Firmendaten anzureichern und priorisiert zu verteilen.',
    difficulty: 'Fortgeschritten',
    duration: 'ca. 1–2 Stunden Setup',
    tools: ['Stripe API', 'Resend API', 'Make', 'OpenAI API'],
    steps: [
      {
        title: 'Lead-Erfassung',
        description:
          'Erfasse Anfragen über Formulare oder Webhooks und normalisiere die Daten in einem einheitlichen Format.',
      },
      {
        title: 'Anreicherung',
        description:
          'Ergänze Firmendaten und prüfe E-Mail-Adressen auf Gültigkeit, um Spam frühzeitig auszufiltern.',
      },
      {
        title: 'KI-Bewertung',
        description:
          'Bewerte den Lead anhand von Kriterien wie Budget, Branche und Dringlichkeit mit einem Sprachmodell.',
      },
      {
        title: 'Routing & Benachrichtigung',
        description:
          'Weise den Lead dem passenden Team zu und versende personalisierte E-Mails über die Resend API.',
      },
    ],
    tags: ['Sales', 'CRM', 'KI', 'Automatisierung'],
  },
  {
    slug: 'programmatic-seo-pipeline',
    title: 'Programmatic-SEO-Pipeline',
    description:
      'Der komplette Workflow für tausende SEO-Seiten: Datenquellen, Template-Engine, Build-Prozess und Monitoring.',
    longDescription:
      'Programmatic SEO lebt von konsistenten Daten und Templates. Diese Pipeline beschreibt, wie du strukturierte Daten pflegst, daraus mit Astro statische Seiten generierst und die Qualität über Monitoring und interne Verlinkung sicherstellst.',
    difficulty: 'Experte',
    duration: 'ca. 1 Tag Setup',
    tools: ['Astro', 'Supabase', 'OpenAI API', 'n8n'],
    steps: [
      {
        title: 'Datenquellen definieren',
        description:
          'Lege fest, welche strukturierten Daten (APIs, Tools, Vergleiche) die Grundlage deiner Seiten bilden.',
      },
      {
        title: 'Templates entwickeln',
        description:
          'Baue dynamische Routen mit getStaticPaths und wiederverwendbaren Komponenten für konsistente Layouts.',
      },
      {
        title: 'Interne Verlinkung',
        description:
          'Verknüpfe verwandte Seiten automatisch, um Crawlability und Relevanz zu stärken.',
      },
      {
        title: 'Build & Deployment',
        description:
          'Generiere alle Seiten statisch und deploye sie über eine CI/CD-Pipeline bei jeder Datenänderung.',
      },
      {
        title: 'Monitoring',
        description:
          'Überwache Indexierung, Rankings und Core Web Vitals und iteriere datenbasiert.',
      },
    ],
    tags: ['SEO', 'Astro', 'Skalierung', 'Deployment'],
  },
];
