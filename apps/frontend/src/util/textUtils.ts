/**
 * Utility functions for text manipulation and display
 */

/**
 * Splits a string into prefix and suffix for dynamic middle ellipsis display.
 * Uses percentage-based calculation to adapt to string length.
 *
 * @param text - The full text string to split
 * @param prefixPercent - Percentage of text to show at the beginning (default: 40%)
 * @param suffixPercent - Percentage of text to show at the end (default: 40%)
 * @param minPrefixChars - Minimum characters for prefix (default: 8)
 * @param minSuffixChars - Minimum characters for suffix (default: 8)
 * @returns Object with prefix and suffix strings
 *
 * @example
 * // For a 50-char string with 30% each:
 * // Returns { prefix: "IMS-11088-CVDP-099" (15 chars), suffix: "B584-0576053368E6" (15 chars) }
 * splitForMiddleEllipsis("IMS-11088-CVDP-09983EA9-4106-43A5-B584-0576053368E6")
 *
 */
export function splitForMiddleEllipsis(
  text: string,
  prefixPercent: number = 30,
  suffixPercent: number = 30,
  minPrefixChars: number = 6,
  minSuffixChars: number = 6,
): { prefix: string; suffix: string; needsEllipsis: boolean } {
  const minLengthForEllipsis = minPrefixChars + minSuffixChars + 3 // +3 for "..."

  // If text is short enough, don't truncate
  if (text.length <= minLengthForEllipsis) {
    return {
      prefix: text,
      suffix: '',
      needsEllipsis: false,
    }
  }

  // Calculate character counts based on percentage
  const prefixLength = Math.max(minPrefixChars, Math.floor((text.length * prefixPercent) / 100))
  const suffixLength = Math.max(minSuffixChars, Math.floor((text.length * suffixPercent) / 100))

  // Ensure we don't exceed total length
  const totalVisible = prefixLength + suffixLength
  if (totalVisible >= text.length - 3) {
    // If combined length is almost the full string, just show it all
    return {
      prefix: text,
      suffix: '',
      needsEllipsis: false,
    }
  }

  // Split into prefix and suffix
  return {
    prefix: text.substring(0, prefixLength),
    suffix: text.substring(text.length - suffixLength),
    needsEllipsis: true,
  }
}

/**
 * Formats a string with middle ellipsis as a single string.
 * Uses percentage-based calculation for dynamic adaptation.
 *
 * @param text - The full text string
 * @param prefixPercent - Percentage of text to show at the beginning (default: 30%)
 * @param suffixPercent - Percentage of text to show at the end (default: 30%)
 * @returns Formatted string with ellipsis in the middle
 *
 * @example
 * // For long IDs: "IMS-11088-...-B584-0576053368E6"
 * formatMiddleEllipsis("IMS-11088-CVDP-09983EA9-4106-43A5-B584-0576053368E6")
 *
 * @example
 * // For short IDs: "SHORT-ID"
 * formatMiddleEllipsis("SHORT-ID")
 */
export function formatMiddleEllipsis(
  text: string,
  prefixPercent: number = 30,
  suffixPercent: number = 30,
): string {
  const { prefix, suffix, needsEllipsis } = splitForMiddleEllipsis(
    text,
    prefixPercent,
    suffixPercent,
  )

  if (!needsEllipsis) {
    return prefix
  }

  return `${prefix}...${suffix}`
}
