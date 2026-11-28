export function isValidPhoneNumber(value) {
  const phone = value.trim()

  if (!/^\+?[\d\s().-]+$/.test(phone)) return false

  let digits = phone.replace(/\D/g, '')
  if (digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1)

  return digits.length === 10 && /^[2-9]\d{2}[2-9]\d{6}$/.test(digits)
}
