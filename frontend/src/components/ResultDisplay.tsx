interface SearchResult {
  status: number;
  title?: string;
  author?: string;
  message?: string;
  distance?: number;
  min_distance?: number;
  vector?: number[];
}

interface UserInputs {
  eraMin: number;
  eraMax: number;
  origin: number;
  style: number;
  renown: number;
}

interface ResultDisplayProps {
  book: SearchResult | null;
  loading: boolean;
  error: string | null;
  userInputs?: UserInputs;
}

export const ResultDisplay: React.FC<ResultDisplayProps> = ({ book, loading, error }) => {
  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-8 w-full">
        <p className="text-gray-400 tracking-[0.4em] text-sm uppercase font-mono">404: NULL SPACE</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center w-full">
        <div className="w-24 h-[1px] bg-gray-800 overflow-hidden relative">
          <div className="absolute top-0 left-0 h-full bg-white w-full animate-[loadingLine_1.5s_ease-in-out_infinite] scale-x-0 origin-left"></div>
        </div>
        <style>{`
          @keyframes loadingLine {
            0% { transform: scaleX(0); transform-origin: left; }
            50% { transform: scaleX(1); transform-origin: left; }
            50.1% { transform: scaleX(1); transform-origin: right; }
            100% { transform: scaleX(0); transform-origin: right; }
          }
        `}</style>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="h-full flex items-center justify-center w-full">
        <div className="text-gray-500 text-xl font-bold tracking-[0.5em] uppercase font-light">
          Awaiting Vector Input
        </div>
      </div>
    );
  }

  const dist = book.distance !== undefined ? book.distance : book.min_distance;

  // 404: 誠実な沈黙
  if (book.status === 404) {
    return (
      <div className="h-full flex flex-col justify-center items-center w-full max-w-2xl px-8 animate-[fadeIn_1s_ease-out]">
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
        <p className="text-gray-400 tracking-[0.4em] text-sm uppercase font-mono">
          404: NULL SPACE
        </p>
      </div>
    );
  }

  // 200: 抽出成功
  return (
    <div className="h-full flex flex-col justify-center w-full max-w-2xl px-8 animate-[fadeIn_1s_ease-out]">
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div className="space-y-8 text-center md:text-left">
        <div className="flex flex-col gap-4 min-w-0">
          <p className="font-mono text-gray-500 tracking-[0.4em] text-xs uppercase mb-2">
            Extraction Complete
          </p>
          <h1 className="font-serif text-5xl leading-tight md:text-6xl lg:text-7xl text-gray-100 break-words font-light">
            {book.title}
          </h1>
          <p className="text-sm text-gray-400 mt-2 tracking-widest uppercase">
            {book.author || "作者不明"}
          </p>
        </div>

        <div className="w-8 h-[1px] bg-gray-700 my-6 mx-auto md:mx-0"></div>

        {/* Stoic Vector Section */}
        {book.vector && (
          <div className="py-2">
            <p className="text-gray-400 font-mono text-xs tracking-[0.2em] leading-loose">
              [ ERA: {book.vector[0].toFixed(2)} | ORIGIN: {book.vector[1].toFixed(2)} | STYLE: {book.vector[2].toFixed(2)} | RENOWN: {book.vector[3].toFixed(2)} ]
            </p>
          </div>
        )}

        {dist !== undefined && (
          <p className="text-gray-400 font-mono text-xs tracking-widest uppercase">
            DISTANCE: {dist.toFixed(4)}
          </p>
        )}
      </div>
    </div>
  );
};
