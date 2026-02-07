/**
 * Twitter Tweet Validation Tool (T056).
 *
 * Validates tweet content before posting:
 * - Character count (280 limit)
 * - URL counting (23 chars per URL)
 * - Emoji handling
 * - Mention validation
 */

import { z } from 'zod';
import { TWEET_CHAR_LIMIT, URL_CHAR_COUNT } from '../lib/twitter_client.js';

/**
 * Input schema for validate_tweet tool.
 */
export const ValidateTweetInputSchema = z.object({
  text: z.string().describe('Tweet text to validate'),
});

export type ValidateTweetInput = z.infer<typeof ValidateTweetInputSchema>;

/**
 * Output schema for validate_tweet tool.
 */
export interface ValidateTweetOutput {
  valid: boolean;
  character_count: number;
  remaining: number;
  limit: number;
  breakdown: {
    text_chars: number;
    url_chars: number;
    url_count: number;
    emoji_count: number;
  };
  warnings: string[];
  suggestions: string[];
  error?: string;
}

/**
 * URL pattern for detection.
 */
const URL_PATTERN = /https?:\/\/\S+/gi;

/**
 * Mention pattern for detection.
 */
const MENTION_PATTERN = /@[\w]+/g;

/**
 * Hashtag pattern for detection.
 */
const HASHTAG_PATTERN = /#[\w]+/g;

/**
 * Count characters using Twitter's weighted character counting.
 *
 * Note: This is a simplified implementation. Twitter's actual
 * character counting is more complex with Unicode normalization.
 */
function countCharacters(text: string): { count: number; emojiCount: number } {
  let count = 0;
  let emojiCount = 0;

  // Iterate through Unicode code points
  for (const char of text) {
    const codePoint = char.codePointAt(0) || 0;

    // Emoji and other special characters (above BMP) count as 2
    if (codePoint > 0xFFFF) {
      count += 2;
      emojiCount += 1;
    } else {
      count += 1;
    }
  }

  return { count, emojiCount };
}

/**
 * Process text to calculate Twitter character count.
 *
 * URLs are replaced with 23-character placeholders.
 */
function processTextForCounting(text: string): {
  processedText: string;
  urlCount: number;
  urlChars: number;
} {
  const urls = text.match(URL_PATTERN) || [];
  const urlCount = urls.length;

  // Calculate actual characters saved/added by URL replacement
  let originalUrlChars = 0;
  for (const url of urls) {
    originalUrlChars += url.length;
  }

  // Replace URLs with 23-char placeholder
  const processedText = text.replace(URL_PATTERN, 'x'.repeat(URL_CHAR_COUNT));

  // URL chars in final count
  const urlChars = urlCount * URL_CHAR_COUNT;

  return { processedText, urlCount, urlChars };
}

/**
 * Generate suggestions for tweets that are too long.
 */
function generateSuggestions(text: string, charCount: number): string[] {
  const suggestions: string[] = [];
  const excess = charCount - TWEET_CHAR_LIMIT;

  if (excess <= 0) {
    return suggestions;
  }

  suggestions.push(`Remove ${excess} character${excess > 1 ? 's' : ''} to meet the limit`);

  // Check for words that could be shortened
  const longWords = text.split(/\s+/).filter(w => w.length > 10);
  if (longWords.length > 0) {
    suggestions.push(`Consider shortening long words: ${longWords.slice(0, 3).join(', ')}`);
  }

  // Check for unnecessary hashtags
  const hashtags = text.match(HASHTAG_PATTERN) || [];
  if (hashtags.length > 3) {
    suggestions.push(`Consider reducing hashtags (currently ${hashtags.length})`);
  }

  // Suggest thread for long content
  if (excess > 50) {
    suggestions.push('Consider splitting into a thread using the auto-thread feature');
  }

  return suggestions;
}

/**
 * Generate warnings about tweet content.
 */
function generateWarnings(text: string): string[] {
  const warnings: string[] = [];

  // Check for common issues
  const urls = text.match(URL_PATTERN) || [];
  const mentions = text.match(MENTION_PATTERN) || [];
  const hashtags = text.match(HASHTAG_PATTERN) || [];

  // Too many mentions (may look spammy)
  if (mentions.length > 5) {
    warnings.push(`High number of mentions (${mentions.length}) may appear spammy`);
  }

  // Too many hashtags
  if (hashtags.length > 5) {
    warnings.push(`High number of hashtags (${hashtags.length}) may reduce engagement`);
  }

  // Multiple URLs
  if (urls.length > 2) {
    warnings.push(`Multiple URLs (${urls.length}) may reduce engagement`);
  }

  // All caps
  const uppercaseRatio = (text.match(/[A-Z]/g) || []).length / text.length;
  if (uppercaseRatio > 0.5 && text.length > 20) {
    warnings.push('Heavy use of CAPS may appear aggressive');
  }

  // Sensitive word check (basic)
  const sensitivePatterns = [
    /\b(free money|make \$|click here)\b/i,
    /\b(dm me|send me)\b/i,
  ];
  for (const pattern of sensitivePatterns) {
    if (pattern.test(text)) {
      warnings.push('Content may trigger spam filters');
      break;
    }
  }

  return warnings;
}

/**
 * Main tool handler for validate_tweet.
 */
export function validateTweet(input: ValidateTweetInput): ValidateTweetOutput {
  const { text } = input;

  // Handle empty text
  if (!text || text.trim().length === 0) {
    return {
      valid: false,
      character_count: 0,
      remaining: TWEET_CHAR_LIMIT,
      limit: TWEET_CHAR_LIMIT,
      breakdown: {
        text_chars: 0,
        url_chars: 0,
        url_count: 0,
        emoji_count: 0,
      },
      warnings: [],
      suggestions: ['Add some content to your tweet'],
      error: 'Tweet text cannot be empty',
    };
  }

  // Process URLs for counting
  const { processedText, urlCount, urlChars } = processTextForCounting(text);

  // Count characters in processed text
  const { count: processedCount, emojiCount } = countCharacters(processedText);

  // Calculate text chars (without URL replacement effect)
  const textChars = processedCount - (urlCount * URL_CHAR_COUNT);

  // Total character count (as Twitter sees it)
  const totalCount = processedCount;

  // Generate warnings and suggestions
  const warnings = generateWarnings(text);
  const suggestions = generateSuggestions(text, totalCount);

  // Determine validity
  const valid = totalCount <= TWEET_CHAR_LIMIT;

  return {
    valid,
    character_count: totalCount,
    remaining: Math.max(0, TWEET_CHAR_LIMIT - totalCount),
    limit: TWEET_CHAR_LIMIT,
    breakdown: {
      text_chars: Math.max(0, textChars),
      url_chars: urlChars,
      url_count: urlCount,
      emoji_count: emojiCount,
    },
    warnings,
    suggestions,
    error: valid ? undefined : `Tweet exceeds ${TWEET_CHAR_LIMIT} character limit (${totalCount} chars)`,
  };
}

/**
 * Suggest how to split long text into a thread.
 */
export function suggestThreadSplit(text: string): {
  recommended: boolean;
  tweet_count: number;
  tweets: string[];
} {
  const validation = validateTweet({ text });

  if (validation.valid) {
    return {
      recommended: false,
      tweet_count: 1,
      tweets: [text],
    };
  }

  // Split into tweets
  const tweets: string[] = [];
  let remaining = text.trim();

  // Reserve space for " (1/N)" suffix
  const maxLength = TWEET_CHAR_LIMIT - 10;

  while (remaining.length > 0) {
    if (remaining.length <= TWEET_CHAR_LIMIT) {
      tweets.push(remaining);
      break;
    }

    // Find a good split point
    let splitAt = remaining.lastIndexOf('. ', maxLength);
    if (splitAt < maxLength / 2) {
      splitAt = remaining.lastIndexOf(' ', maxLength);
    }
    if (splitAt < maxLength / 2) {
      splitAt = maxLength;
    }

    tweets.push(remaining.slice(0, splitAt).trim());
    remaining = remaining.slice(splitAt).trim();
  }

  // Add numbering
  const numberedTweets = tweets.map((tweet, i) => `${tweet} (${i + 1}/${tweets.length})`);

  return {
    recommended: true,
    tweet_count: tweets.length,
    tweets: numberedTweets,
  };
}
