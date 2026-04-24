/** Map `/api/user/me` to total and remaining generations (student vs teacher). */
export function computeGenerationsFromMeResponse(data) {
  if (!data || !data.id) {
    return { user: null, generationsTotal: null, generationsRemaining: null };
  }
  const gn = data.generations_number || 0;
  if (data.persona === "teacher") {
    return { user: data, generationsTotal: 5, generationsRemaining: 5 - gn };
  }
  if (data.persona === "student") {
    return { user: data, generationsTotal: 3, generationsRemaining: 3 - gn };
  }
  return { user: data, generationsTotal: null, generationsRemaining: null };
}
