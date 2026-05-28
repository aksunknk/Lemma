import { useState } from 'react';
import { InputPanel } from './components/InputPanel';
import { ResultDisplay, SearchResult } from './components/ResultDisplay';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.node4d.xyz';
const EXTRACTION_DELAY_MS = 800;

function App() {
  const [query, setQuery] = useState('');
  const [eraMin, setEraMin] = useState(0.0);
  const [eraMax, setEraMax] = useState(1.0);
  const [origin, setOrigin] = useState(0.5);
  const [style, setStyle] = useState(0.5);
  const [renown, setRenown] = useState(0.5);
  
  const [book, setBook] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    setBook(null);

    const payload = { 
      query: query || null, 
      era_min: eraMin, 
      era_max: eraMax, 
      origin, 
      style, 
      renown,
      keyword: null, 
    };

    try {
      await new Promise(resolve => setTimeout(resolve, EXTRACTION_DELAY_MS));

      const res = await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.status === 404) {
        setBook({ status: 404 });
        return;
      }

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Network response was not ok');
      }

      setBook(await res.json());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred during extraction.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-brand-950 text-brand-50 font-sans">
      <div className="absolute inset-0 z-0 pointer-events-none opacity-[0.03]" 
        style={{
          backgroundImage: `radial-gradient(circle at center, #ffffff 1px, transparent 1px)`,
          backgroundSize: `48px 48px`
        }}>
      </div>
      
      <div className="w-full md:w-[45%] lg:w-[35%] flex flex-col border-b md:border-b-0 md:border-r border-gray-900 justify-between p-8 md:p-14 lg:p-16 relative z-10 bg-brand-950/90 backdrop-blur-sm shadow-2xl overflow-y-auto md:max-h-screen">
        <div className="mb-10">
          <h2 className="text-[9px] tracking-[0.5em] text-gray-500 uppercase leading-loose">
            Lemma Singular Book<br/>Extraction Engine
          </h2>
          <div className="w-6 h-[1px] bg-gray-700 mt-6"></div>
        </div>
        
        <div className="flex-grow flex flex-col justify-center">
          <InputPanel 
            query={query} setQuery={setQuery}
            eraMin={eraMin} setEraMin={setEraMin}
            eraMax={eraMax} setEraMax={setEraMax}
            origin={origin} setOrigin={setOrigin}
            style={style} setStyle={setStyle}
            renown={renown} setRenown={setRenown}
            onSubmit={handleSearch}
            isLoading={loading}
          />
        </div>
        
        <div className="mt-10 text-[8px] tracking-[0.4em] text-gray-700 uppercase font-mono">
          Model: 384D Hybrid Vector Space
        </div>
      </div>

      <div className="flex-1 relative flex items-center justify-center p-8 md:p-16 z-10 min-h-[60vh] md:min-h-screen">
        <ResultDisplay 
          book={book} 
          loading={loading} 
          error={error} 
        />
      </div>
    </div>
  );
}

export default App;
