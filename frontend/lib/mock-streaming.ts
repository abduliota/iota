export function mockStreamResponse(
  text: string,
  onChunk: (chunk: string) => void,
  onComplete: () => void
): void {
  const words = text.split(' ');
  let index = 0;
  
  const stream = () => {
    if (index < words.length) {
      const chunk = index === 0 ? words[index] : ' ' + words[index];
      onChunk(chunk);
      index++;
      setTimeout(stream, 30 + Math.random() * 50);
    } else {
      onComplete();
    }
  };
  
  stream();
}
