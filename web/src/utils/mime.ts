export const mimeAliases: Record<string, string> = {
  // Office
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
  'application/vnd.ms-excel': 'Excel (старый)',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
  'application/msword': 'Word (старый)',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint',
  'application/vnd.ms-powerpoint': 'PowerPoint (старый)',

  // PDF / текст
  'application/pdf': 'PDF',
  'text/plain': 'TXT',
  'text/csv': 'CSV',
  'application/rtf': 'RTF',

  // Изображения
  'image/jpeg': 'JPEG',
  'image/png': 'PNG',
  'image/gif': 'GIF',
  'image/webp': 'WebP',
  'image/svg+xml': 'SVG',
  'image/bmp': 'BMP',
  'image/tiff': 'TIFF',

  // Аудио
  'audio/mpeg': 'MP3',
  'audio/wav': 'WAV',
  'audio/ogg': 'OGG',
  'audio/flac': 'FLAC',
  'audio/aac': 'AAC',

  // Видео
  'video/mp4': 'MP4',
  'video/mpeg': 'MPEG',
  'video/ogg': 'OGG',
  'video/webm': 'WebM',
  'video/quicktime': 'MOV',

  // Архивы
  'application/zip': 'ZIP',
  'application/x-rar-compressed': 'RAR',
  'application/gzip': 'GZIP',
  'application/x-7z-compressed': '7Z',
  'application/x-tar': 'TAR',

  // Программные файлы
  'application/javascript': 'JS',
  'text/html': 'HTML',
  'text/css': 'CSS',
  'application/json': 'JSON',
  'application/xml': 'XML',

  // Другие популярные
  'application/octet-stream': 'BIN',
  'application/x-sh': 'Shell Script',
  'text/x-python': 'Python',
}
