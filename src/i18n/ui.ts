/**
 * Lightweight client-side i18n for the UI chrome.
 *
 * The site content itself is English (default). The language switcher
 * translates the main UI strings (navigation, hero, categories, CTA, footer)
 * into the selected language. Additional keys can be added over time.
 */

export interface Language {
  code: string;
  country: string;
  flag: string;
  name: string;
}

// Active locales. Additional translations may exist below, but only these
// locales are built and exposed in the language switcher.
export const languages: Language[] = [
  { code: "en", country: "GB", flag: "🇬🇧", name: "English" },
  { code: "de", country: "DE", flag: "🇩🇪", name: "Deutsch" },
];

export type TranslationKey =
  | "nav.apis"
  | "nav.alternatives"
  | "nav.workflows"
  | "hero.badge"
  | "hero.title1"
  | "hero.title2"
  | "hero.subtitle"
  | "hero.ctaApis"
  | "hero.ctaWorkflows"
  | "stats.apis"
  | "stats.alternatives"
  | "stats.workflows"
  | "stats.open"
  | "categories.title"
  | "categories.subtitle"
  | "cat.apis.label"
  | "cat.apis.title"
  | "cat.apis.desc"
  | "cat.alt.label"
  | "cat.alt.title"
  | "cat.alt.desc"
  | "cat.wf.label"
  | "cat.wf.title"
  | "cat.wf.desc"
  | "cta.title"
  | "cta.desc"
  | "cta.start"
  | "cta.compare"
  | "footer.tagline"
  | "footer.imprint"
  | "footer.privacy"
  | "footer.visitors";

export const translations: Record<string, Record<TranslationKey, string>> = {
  en: {
    "nav.apis": "APIs",
    "nav.alternatives": "Alternatives",
    "nav.workflows": "Workflows",
    "hero.badge": "FlowMatrix · curated & current",
    "hero.title1": "The knowledge hub for",
    "hero.title2": "APIs, alternatives and workflows",
    "hero.subtitle":
      "Structured, searchable content for developers and SEO teams. Find the right API, compare alternatives and build scalable automations.",
    "hero.ctaApis": "Explore APIs",
    "hero.ctaWorkflows": "View workflows",
    "stats.apis": "APIs",
    "stats.alternatives": "Alternatives",
    "stats.workflows": "Workflows",
    "stats.open": "Open content",
    "categories.title": "Three categories, one hub",
    "categories.subtitle":
      "Choose an area and dive into structured, linked content.",
    "cat.apis.label": "Interfaces",
    "cat.apis.title": "APIs",
    "cat.apis.desc":
      "Curated APIs for AI, payments, backend and communication – with features, pricing and ratings.",
    "cat.alt.label": "Comparisons",
    "cat.alt.title": "Alternatives",
    "cat.alt.desc":
      "The best alternatives to popular tools – with pros, cons, pricing and target audiences.",
    "cat.wf.label": "Automation",
    "cat.wf.title": "Workflows",
    "cat.wf.desc":
      "Step-by-step workflows for content, sales and programmatic SEO – including the tool stack.",
    "cta.title": "Ready to scale your programmatic SEO project?",
    "cta.desc":
      "Start with the APIs, compare alternatives and automate your workflows – all in one place.",
    "cta.start": "Get started",
    "cta.compare": "Compare alternatives",
    "footer.tagline":
      "Curated APIs, alternatives and workflows for modern product and SEO teams.",
    "footer.imprint": "Imprint",
    "footer.privacy": "Privacy",
    "footer.visitors": "visitors",
  },
  de: {
    "nav.apis": "APIs",
    "nav.alternatives": "Alternativen",
    "nav.workflows": "Workflows",
    "hero.badge": "FlowMatrix · kuratiert & aktuell",
    "hero.title1": "Das Wissens-Hub für",
    "hero.title2": "APIs, Alternativen und Workflows",
    "hero.subtitle":
      "Strukturierte, durchsuchbare Inhalte für Entwickler und SEO-Teams. Finde die passende API, vergleiche Alternativen und baue skalierbare Automatisierungen.",
    "hero.ctaApis": "APIs entdecken",
    "hero.ctaWorkflows": "Workflows ansehen",
    "stats.apis": "APIs",
    "stats.alternatives": "Alternativen",
    "stats.workflows": "Workflows",
    "stats.open": "Offene Inhalte",
    "categories.title": "Drei Kategorien, ein Hub",
    "categories.subtitle":
      "Wähle einen Bereich und tauche in strukturierte, verlinkte Inhalte ein.",
    "cat.apis.label": "Schnittstellen",
    "cat.apis.title": "APIs",
    "cat.apis.desc":
      "Kuratierte APIs für KI, Payments, Backend und Kommunikation – mit Features, Preisen und Bewertungen.",
    "cat.alt.label": "Vergleiche",
    "cat.alt.title": "Alternativen",
    "cat.alt.desc":
      "Die besten Alternativen zu bekannten Tools – mit Vor- und Nachteilen, Preisen und Zielgruppen.",
    "cat.wf.label": "Automatisierung",
    "cat.wf.title": "Workflows",
    "cat.wf.desc":
      "Schritt-für-Schritt-Workflows für Content, Sales und Programmatic SEO – inklusive Tool-Stack.",
    "cta.title": "Bereit, dein Programmatic-SEO-Projekt zu skalieren?",
    "cta.desc":
      "Starte mit den APIs, vergleiche Alternativen und automatisiere deine Workflows – alles an einem Ort.",
    "cta.start": "Jetzt starten",
    "cta.compare": "Alternativen vergleichen",
    "footer.tagline":
      "Kuratierte APIs, Alternativen und Workflows für moderne Produkt- und SEO-Teams.",
    "footer.imprint": "Impressum",
    "footer.privacy": "Datenschutz",
    "footer.visitors": "Besucher",
  },
  fr: {
    "nav.apis": "API",
    "nav.alternatives": "Alternatives",
    "nav.workflows": "Workflows",
    "hero.badge": "FlowMatrix · sélectionné et à jour",
    "hero.title1": "Le hub de connaissances pour",
    "hero.title2": "API, alternatives et workflows",
    "hero.subtitle":
      "Des contenus structurés et recherchables pour les développeurs et les équipes SEO. Trouvez la bonne API, comparez les alternatives et créez des automatisations évolutives.",
    "hero.ctaApis": "Explorer les API",
    "hero.ctaWorkflows": "Voir les workflows",
    "stats.apis": "API",
    "stats.alternatives": "Alternatives",
    "stats.workflows": "Workflows",
    "stats.open": "Contenu ouvert",
    "categories.title": "Trois catégories, un hub",
    "categories.subtitle":
      "Choisissez un domaine et plongez dans un contenu structuré et lié.",
    "cat.apis.label": "Interfaces",
    "cat.apis.title": "API",
    "cat.apis.desc":
      "Des API sélectionnées pour l'IA, les paiements, le backend et la communication – avec fonctionnalités, prix et notes.",
    "cat.alt.label": "Comparaisons",
    "cat.alt.title": "Alternatives",
    "cat.alt.desc":
      "Les meilleures alternatives aux outils populaires – avec avantages, inconvénients, prix et publics cibles.",
    "cat.wf.label": "Automatisation",
    "cat.wf.title": "Workflows",
    "cat.wf.desc":
      "Des workflows étape par étape pour le contenu, les ventes et le SEO programmatique – avec la stack d'outils.",
    "cta.title": "Prêt à faire évoluer votre projet de SEO programmatique ?",
    "cta.desc":
      "Commencez par les API, comparez les alternatives et automatisez vos workflows – au même endroit.",
    "cta.start": "Commencer",
    "cta.compare": "Comparer les alternatives",
    "footer.tagline":
      "Des API, alternatives et workflows sélectionnés pour les équipes produit et SEO modernes.",
    "footer.imprint": "Mentions légales",
    "footer.privacy": "Confidentialité",
    "footer.visitors": "visiteurs",
  },
  es: {
    "nav.apis": "APIs",
    "nav.alternatives": "Alternativas",
    "nav.workflows": "Flujos de trabajo",
    "hero.badge": "FlowMatrix · curado y actualizado",
    "hero.title1": "El centro de conocimiento para",
    "hero.title2": "APIs, alternativas y flujos de trabajo",
    "hero.subtitle":
      "Contenido estructurado y buscable para desarrolladores y equipos SEO. Encuentra la API adecuada, compara alternativas y crea automatizaciones escalables.",
    "hero.ctaApis": "Explorar APIs",
    "hero.ctaWorkflows": "Ver flujos de trabajo",
    "stats.apis": "APIs",
    "stats.alternatives": "Alternativas",
    "stats.workflows": "Flujos",
    "stats.open": "Contenido abierto",
    "categories.title": "Tres categorías, un centro",
    "categories.subtitle":
      "Elige un área y sumérgete en contenido estructurado y enlazado.",
    "cat.apis.label": "Interfaces",
    "cat.apis.title": "APIs",
    "cat.apis.desc":
      "APIs seleccionadas para IA, pagos, backend y comunicación – con funciones, precios y valoraciones.",
    "cat.alt.label": "Comparativas",
    "cat.alt.title": "Alternativas",
    "cat.alt.desc":
      "Las mejores alternativas a herramientas populares – con ventajas, desventajas, precios y públicos.",
    "cat.wf.label": "Automatización",
    "cat.wf.title": "Flujos de trabajo",
    "cat.wf.desc":
      "Flujos paso a paso para contenido, ventas y SEO programático – incluido el stack de herramientas.",
    "cta.title": "¿Listo para escalar tu proyecto de SEO programático?",
    "cta.desc":
      "Empieza con las APIs, compara alternativas y automatiza tus flujos – todo en un solo lugar.",
    "cta.start": "Empezar",
    "cta.compare": "Comparar alternativas",
    "footer.tagline":
      "APIs, alternativas y flujos de trabajo seleccionados para equipos de producto y SEO modernos.",
    "footer.imprint": "Aviso legal",
    "footer.privacy": "Privacidad",
    "footer.visitors": "visitantes",
  },
  it: {
    "nav.apis": "API",
    "nav.alternatives": "Alternative",
    "nav.workflows": "Workflow",
    "hero.badge": "FlowMatrix · curato e aggiornato",
    "hero.title1": "L'hub di conoscenza per",
    "hero.title2": "API, alternative e workflow",
    "hero.subtitle":
      "Contenuti strutturati e ricercabili per sviluppatori e team SEO. Trova l'API giusta, confronta le alternative e crea automazioni scalabili.",
    "hero.ctaApis": "Esplora le API",
    "hero.ctaWorkflows": "Vedi i workflow",
    "stats.apis": "API",
    "stats.alternatives": "Alternative",
    "stats.workflows": "Workflow",
    "stats.open": "Contenuto aperto",
    "categories.title": "Tre categorie, un hub",
    "categories.subtitle":
      "Scegli un'area e immergiti in contenuti strutturati e collegati.",
    "cat.apis.label": "Interfacce",
    "cat.apis.title": "API",
    "cat.apis.desc":
      "API selezionate per IA, pagamenti, backend e comunicazione – con funzionalità, prezzi e valutazioni.",
    "cat.alt.label": "Confronti",
    "cat.alt.title": "Alternative",
    "cat.alt.desc":
      "Le migliori alternative agli strumenti più diffusi – con pro, contro, prezzi e pubblico.",
    "cat.wf.label": "Automazione",
    "cat.wf.title": "Workflow",
    "cat.wf.desc":
      "Workflow passo passo per contenuti, vendite e SEO programmatica – incluso lo stack di strumenti.",
    "cta.title": "Pronto a scalare il tuo progetto di SEO programmatica?",
    "cta.desc":
      "Inizia dalle API, confronta le alternative e automatizza i tuoi workflow – tutto in un unico posto.",
    "cta.start": "Inizia",
    "cta.compare": "Confronta le alternative",
    "footer.tagline":
      "API, alternative e workflow selezionati per team di prodotto e SEO moderni.",
    "footer.imprint": "Note legali",
    "footer.privacy": "Privacy",
    "footer.visitors": "visitatori",
  },
  pt: {
    "nav.apis": "APIs",
    "nav.alternatives": "Alternativas",
    "nav.workflows": "Fluxos de trabalho",
    "hero.badge": "FlowMatrix · curado e atualizado",
    "hero.title1": "O hub de conhecimento para",
    "hero.title2": "APIs, alternativas e fluxos de trabalho",
    "hero.subtitle":
      "Conteúdo estruturado e pesquisável para desenvolvedores e equipes de SEO. Encontre a API certa, compare alternativas e crie automações escaláveis.",
    "hero.ctaApis": "Explorar APIs",
    "hero.ctaWorkflows": "Ver fluxos de trabalho",
    "stats.apis": "APIs",
    "stats.alternatives": "Alternativas",
    "stats.workflows": "Fluxos",
    "stats.open": "Conteúdo aberto",
    "categories.title": "Três categorias, um hub",
    "categories.subtitle":
      "Escolha uma área e mergulhe em conteúdo estruturado e interligado.",
    "cat.apis.label": "Interfaces",
    "cat.apis.title": "APIs",
    "cat.apis.desc":
      "APIs selecionadas para IA, pagamentos, backend e comunicação – com recursos, preços e avaliações.",
    "cat.alt.label": "Comparações",
    "cat.alt.title": "Alternativas",
    "cat.alt.desc":
      "As melhores alternativas a ferramentas populares – com prós, contras, preços e públicos.",
    "cat.wf.label": "Automação",
    "cat.wf.title": "Fluxos de trabalho",
    "cat.wf.desc":
      "Fluxos passo a passo para conteúdo, vendas e SEO programático – incluindo o stack de ferramentas.",
    "cta.title": "Pronto para escalar seu projeto de SEO programático?",
    "cta.desc":
      "Comece pelas APIs, compare alternativas e automatize seus fluxos – tudo em um só lugar.",
    "cta.start": "Começar",
    "cta.compare": "Comparar alternativas",
    "footer.tagline":
      "APIs, alternativas e fluxos de trabalho selecionados para equipes de produto e SEO modernas.",
    "footer.imprint": "Aviso legal",
    "footer.privacy": "Privacidade",
    "footer.visitors": "visitantes",
  },
  nl: {
    "nav.apis": "API's",
    "nav.alternatives": "Alternatieven",
    "nav.workflows": "Workflows",
    "hero.badge": "FlowMatrix · gecureerd en actueel",
    "hero.title1": "De kennis hub voor",
    "hero.title2": "API's, alternatieven en workflows",
    "hero.subtitle":
      "Gestructureerde, doorzoekbare content voor ontwikkelaars en SEO-teams. Vind de juiste API, vergelijk alternatieven en bouw schaalbare automatiseringen.",
    "hero.ctaApis": "API's verkennen",
    "hero.ctaWorkflows": "Workflows bekijken",
    "stats.apis": "API's",
    "stats.alternatives": "Alternatieven",
    "stats.workflows": "Workflows",
    "stats.open": "Open content",
    "categories.title": "Drie categorieën, één hub",
    "categories.subtitle":
      "Kies een gebied en duik in gestructureerde, gelinkte content.",
    "cat.apis.label": "Interfaces",
    "cat.apis.title": "API's",
    "cat.apis.desc":
      "Gecureerde API's voor AI, betalingen, backend en communicatie – met functies, prijzen en beoordelingen.",
    "cat.alt.label": "Vergelijkingen",
    "cat.alt.title": "Alternatieven",
    "cat.alt.desc":
      "De beste alternatieven voor populaire tools – met voor- en nadelen, prijzen en doelgroepen.",
    "cat.wf.label": "Automatisering",
    "cat.wf.title": "Workflows",
    "cat.wf.desc":
      "Stapsgewijze workflows voor content, sales en programmatic SEO – inclusief de toolstack.",
    "cta.title": "Klaar om je programmatic SEO-project op te schalen?",
    "cta.desc":
      "Begin met de API's, vergelijk alternatieven en automatiseer je workflows – alles op één plek.",
    "cta.start": "Aan de slag",
    "cta.compare": "Alternatieven vergelijken",
    "footer.tagline":
      "Gecureerde API's, alternatieven en workflows voor moderne product- en SEO-teams.",
    "footer.imprint": "Colofon",
    "footer.privacy": "Privacy",
    "footer.visitors": "bezoekers",
  },
  pl: {
    "nav.apis": "API",
    "nav.alternatives": "Alternatywy",
    "nav.workflows": "Workflowy",
    "hero.badge": "FlowMatrix · wyselekcjonowane i aktualne",
    "hero.title1": "Centrum wiedzy o",
    "hero.title2": "API, alternatywach i workflowach",
    "hero.subtitle":
      "Uporządkowane, przeszukiwalne treści dla deweloperów i zespołów SEO. Znajdź odpowiednie API, porównaj alternatywy i buduj skalowalne automatyzacje.",
    "hero.ctaApis": "Odkryj API",
    "hero.ctaWorkflows": "Zobacz workflowy",
    "stats.apis": "API",
    "stats.alternatives": "Alternatywy",
    "stats.workflows": "Workflowy",
    "stats.open": "Otwarte treści",
    "categories.title": "Trzy kategorie, jedno centrum",
    "categories.subtitle":
      "Wybierz obszar i zanurz się w uporządkowanych, powiązanych treściach.",
    "cat.apis.label": "Interfejsy",
    "cat.apis.title": "API",
    "cat.apis.desc":
      "Wyselekcjonowane API do AI, płatności, backendu i komunikacji – z funkcjami, cenami i ocenami.",
    "cat.alt.label": "Porównania",
    "cat.alt.title": "Alternatywy",
    "cat.alt.desc":
      "Najlepsze alternatywy dla popularnych narzędzi – z zaletami, wadami, cenami i grupami docelowymi.",
    "cat.wf.label": "Automatyzacja",
    "cat.wf.title": "Workflowy",
    "cat.wf.desc":
      "Workflowy krok po kroku dla treści, sprzedaży i programmatic SEO – wraz ze stackiem narzędzi.",
    "cta.title": "Gotowy, by skalować swój projekt programmatic SEO?",
    "cta.desc":
      "Zacznij od API, porównaj alternatywy i automatyzuj workflowy – wszystko w jednym miejscu.",
    "cta.start": "Zacznij",
    "cta.compare": "Porównaj alternatywy",
    "footer.tagline":
      "Wyselekcjonowane API, alternatywy i workflowy dla nowoczesnych zespołów produktowych i SEO.",
    "footer.imprint": "Nota prawna",
    "footer.privacy": "Prywatność",
    "footer.visitors": "odwiedzających",
  },
  sv: {
    "nav.apis": "API:er",
    "nav.alternatives": "Alternativ",
    "nav.workflows": "Arbetsflöden",
    "hero.badge": "FlowMatrix · kurerat och aktuellt",
    "hero.title1": "Kunskapshubben för",
    "hero.title2": "API:er, alternativ och arbetsflöden",
    "hero.subtitle":
      "Strukturerat, sökbart innehåll för utvecklare och SEO-team. Hitta rätt API, jämför alternativ och bygg skalbara automatiseringar.",
    "hero.ctaApis": "Utforska API:er",
    "hero.ctaWorkflows": "Visa arbetsflöden",
    "stats.apis": "API:er",
    "stats.alternatives": "Alternativ",
    "stats.workflows": "Arbetsflöden",
    "stats.open": "Öppet innehåll",
    "categories.title": "Tre kategorier, en hubb",
    "categories.subtitle":
      "Välj ett område och dyka ner i strukturerat, länkat innehåll.",
    "cat.apis.label": "Gränssnitt",
    "cat.apis.title": "API:er",
    "cat.apis.desc":
      "Kurerade API:er för AI, betalningar, backend och kommunikation – med funktioner, priser och betyg.",
    "cat.alt.label": "Jämförelser",
    "cat.alt.title": "Alternativ",
    "cat.alt.desc":
      "De bästa alternativen till populära verktyg – med fördelar, nackdelar, priser och målgrupper.",
    "cat.wf.label": "Automatisering",
    "cat.wf.title": "Arbetsflöden",
    "cat.wf.desc":
      "Steg-för-steg-arbetsflöden för innehåll, försäljning och programmatic SEO – inklusive verktygsstacken.",
    "cta.title": "Redo att skala ditt programmatic SEO-projekt?",
    "cta.desc":
      "Börja med API:erna, jämför alternativ och automatisera dina arbetsflöden – allt på ett ställe.",
    "cta.start": "Kom igång",
    "cta.compare": "Jämför alternativ",
    "footer.tagline":
      "Kurerade API:er, alternativ och arbetsflöden för moderna produkt- och SEO-team.",
    "footer.imprint": "Impressum",
    "footer.privacy": "Integritet",
    "footer.visitors": "besökare",
  },
  tr: {
    "nav.apis": "API'ler",
    "nav.alternatives": "Alternatifler",
    "nav.workflows": "İş akışları",
    "hero.badge": "FlowMatrix · seçkin ve güncel",
    "hero.title1": "Bilgi merkezi:",
    "hero.title2": "API'ler, alternatifler ve iş akışları",
    "hero.subtitle":
      "Geliştiriciler ve SEO ekipleri için yapılandırılmış, aranabilir içerik. Doğru API'yi bulun, alternatifleri karşılaştırın ve ölçeklenebilir otomasyonlar kurun.",
    "hero.ctaApis": "API'leri keşfet",
    "hero.ctaWorkflows": "İş akışlarını gör",
    "stats.apis": "API'ler",
    "stats.alternatives": "Alternatifler",
    "stats.workflows": "İş akışları",
    "stats.open": "Açık içerik",
    "categories.title": "Üç kategori, tek merkez",
    "categories.subtitle":
      "Bir alan seçin ve yapılandırılmış, bağlantılı içeriğe dalın.",
    "cat.apis.label": "Arayüzler",
    "cat.apis.title": "API'ler",
    "cat.apis.desc":
      "Yapay zeka, ödemeler, backend ve iletişim için seçkin API'ler – özellikler, fiyatlar ve puanlarla.",
    "cat.alt.label": "Karşılaştırmalar",
    "cat.alt.title": "Alternatifler",
    "cat.alt.desc":
      "Popüler araçlara en iyi alternatifler – artılar, eksiler, fiyatlar ve hedef kitlelerle.",
    "cat.wf.label": "Otomasyon",
    "cat.wf.title": "İş akışları",
    "cat.wf.desc":
      "İçerik, satış ve programmatic SEO için adım adım iş akışları – araç yığını dahil.",
    "cta.title": "Programmatic SEO projenizi ölçeklemeye hazır mısınız?",
    "cta.desc":
      "API'lerle başlayın, alternatifleri karşılaştırın ve iş akışlarınızı otomatikleştirin – hepsi tek yerde.",
    "cta.start": "Başla",
    "cta.compare": "Alternatifleri karşılaştır",
    "footer.tagline":
      "Modern ürün ve SEO ekipleri için seçkin API'ler, alternatifler ve iş akışları.",
    "footer.imprint": "Künye",
    "footer.privacy": "Gizlilik",
    "footer.visitors": "ziyaretçi",
  },
  ja: {
    "nav.apis": "API",
    "nav.alternatives": "代替ツール",
    "nav.workflows": "ワークフロー",
    "hero.badge": "FlowMatrix · 厳選・最新",
    "hero.title1": "ナレッジハブ：",
    "hero.title2": "API・代替ツール・ワークフロー",
    "hero.subtitle":
      "開発者とSEOチームのための構造化された検索可能なコンテンツ。適切なAPIを見つけ、代替ツールを比較し、スケーラブルな自動化を構築しましょう。",
    "hero.ctaApis": "APIを探す",
    "hero.ctaWorkflows": "ワークフローを見る",
    "stats.apis": "API",
    "stats.alternatives": "代替ツール",
    "stats.workflows": "ワークフロー",
    "stats.open": "オープンコンテンツ",
    "categories.title": "3つのカテゴリ、1つのハブ",
    "categories.subtitle":
      "分野を選んで、構造化されたリンク付きコンテンツを探索しましょう。",
    "cat.apis.label": "インターフェース",
    "cat.apis.title": "API",
    "cat.apis.desc":
      "AI、決済、バックエンド、コミュニケーション向けの厳選API – 機能、料金、評価付き。",
    "cat.alt.label": "比較",
    "cat.alt.title": "代替ツール",
    "cat.alt.desc":
      "人気ツールの最適な代替案 – 長所、短所、料金、対象ユーザー付き。",
    "cat.wf.label": "自動化",
    "cat.wf.title": "ワークフロー",
    "cat.wf.desc":
      "コンテンツ、営業、Programmatic SEO向けのステップバイステップのワークフロー – ツールスタック付き。",
    "cta.title": "Programmatic SEOプロジェクトを拡張する準備はできましたか？",
    "cta.desc":
      "APIから始め、代替ツールを比較し、ワークフローを自動化 – すべて一か所で。",
    "cta.start": "始める",
    "cta.compare": "代替ツールを比較",
    "footer.tagline":
      "現代のプロダクト・SEOチーム向けに厳選されたAPI、代替ツール、ワークフロー。",
    "footer.imprint": "運営者情報",
    "footer.privacy": "プライバシー",
    "footer.visitors": "訪問者",
  },
  zh: {
    "nav.apis": "API",
    "nav.alternatives": "替代方案",
    "nav.workflows": "工作流",
    "hero.badge": "FlowMatrix · 精选且及时",
    "hero.title1": "知识中心：",
    "hero.title2": "API、替代方案与工作流",
    "hero.subtitle":
      "为开发者和 SEO 团队打造的结构化、可搜索内容。找到合适的 API，比较替代方案，构建可扩展的自动化。",
    "hero.ctaApis": "探索 API",
    "hero.ctaWorkflows": "查看工作流",
    "stats.apis": "API",
    "stats.alternatives": "替代方案",
    "stats.workflows": "工作流",
    "stats.open": "开放内容",
    "categories.title": "三大类别，一个中心",
    "categories.subtitle": "选择一个领域，深入结构化的关联内容。",
    "cat.apis.label": "接口",
    "cat.apis.title": "API",
    "cat.apis.desc":
      "精选 AI、支付、后端和通信 API – 包含功能、价格和评分。",
    "cat.alt.label": "对比",
    "cat.alt.title": "替代方案",
    "cat.alt.desc":
      "热门工具的最佳替代方案 – 包含优缺点、价格和目标用户。",
    "cat.wf.label": "自动化",
    "cat.wf.title": "工作流",
    "cat.wf.desc":
      "面向内容、销售和 Programmatic SEO 的分步工作流 – 包含工具栈。",
    "cta.title": "准备好扩展你的 Programmatic SEO 项目了吗？",
    "cta.desc":
      "从 API 开始，比较替代方案，自动化你的工作流 – 一切尽在一处。",
    "cta.start": "开始",
    "cta.compare": "比较替代方案",
    "footer.tagline":
      "为现代产品和 SEO 团队精选的 API、替代方案和工作流。",
    "footer.imprint": "法律声明",
    "footer.privacy": "隐私",
    "footer.visitors": "访客",
  },
};
