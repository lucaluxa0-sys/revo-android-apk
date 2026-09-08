
export function capitalizeFirstLetter(str: string): string {
    if (!str) return str; // Handle empty or null strings
    return str.charAt(0).toUpperCase() + str.slice(1);
}
