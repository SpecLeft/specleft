// Sample API module for discovery tests

export function getUser(userId: number): {id: number} {
  return { id: userId };
}

export function createUser(payload: {name: string}): {name: string} {
  return payload;
}
