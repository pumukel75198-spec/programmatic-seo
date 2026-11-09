export interface RelevanceItem {
  title?: string;
  summary?: string;
  category?: string;
  feed?: string;
}

export declare const MIN_ARTICLE_WORDS: number;
export declare const NICHE_TERMS: string[];

export declare function relevanceScore(item: RelevanceItem): number;
export declare function isRelevant(
  item: RelevanceItem,
  minScore?: number,
): boolean;
export declare function normalizeTitle(title: string): string[];
export declare function jaccardSimilarity(a: string, b: string): number;
export declare function isDuplicateTitle(
  title: string,
  existingTitles: string[],
  threshold?: number,
): boolean;
export declare function wordCount(text: string): number;
