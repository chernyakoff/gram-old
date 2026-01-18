export function formatBytes(
  bytes: number,
  options?: {
    decimals?: number
    binary?: boolean
  },
): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '0 B'

  const { decimals = 2, binary = true } = options ?? {}

  const base = binary ? 1024 : 1000
  const units = binary
    ? ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
    : ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

  if (bytes === 0) return '0 B'

  const i = Math.floor(Math.log(bytes) / Math.log(base))
  const value = bytes / Math.pow(base, i)

  return `${value.toFixed(i === 0 ? 0 : decimals)} ${units[i]}`
}
