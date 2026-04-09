import { useState } from 'react';
import { InputPanel } from './components/InputPanel';
import { ResultDisplay } from './components/ResultDisplay';

function App() {
  const [eraMin, setEraMin] = useState<number>(0.0);
  const [eraMax, setEraMax] = useState<number>(1.0);
  const [origin, setOrigin] = useState<number>(0.5);
  const [style, setStyle] = useState<number>(0.5);
  const [renown, setRenown] = useState<number>(0.5);
  const [keyword, setKeyword] = useState<string>('');
  
  const [book, setBook] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    setBook(null);

    // eraMin / eraMax および keyword を含む範囲指定ペイロードを送信
    const payload = { 
      era_min: eraMin, 
      era_max: eraMax, 
      origin, 
      style, 
      renown,
      keyword: keyword || null
    };

    try {
      // 意図的な遅延 — 「抽出」の演出
      await new Promise(resolve => setTimeout(resolve, 800));

      const res = await fetch('https://api.node4d.xyz/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (res.status === 404) {
        setBook(null);
        setError(null);
        return;
      }

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Network response was not ok');
      }

      const data = await res.json();
      setBook(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred during extraction.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-brand-950 text-brand-50 font-sans">
      {/* Background Decor */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-[0.03]" 
        style={{
          backgroundImage: `radial-gradient(circle at center, #ffffff 1px, transparent 1px)`,
          backgroundSize: `48px 48px`
        }}>
      </div>
      
      {/* Left Panel - Inputs */}
      <div className="w-full md:w-[45%] lg:w-[35%] flex flex-col border-b md:border-b-0 md:border-r border-gray-900 justify-between p-8 md:p-14 lg:p-16 relative z-10 bg-brand-950/90 backdrop-blur-sm shadow-2xl overflow-y-auto md:max-h-screen">
        <div className="mb-10">
          <h2 className="text-[9px] tracking-[0.5em] text-gray-500 uppercase leading-loose">
            Singular Book<br/>Extraction Engine
          </h2>
          <div className="w-6 h-[1px] bg-gray-700 mt-6"></div>
        </div>
        
        <div className="flex-grow flex flex-col justify-center">
          <InputPanel 
            eraMin={eraMin} setEraMin={setEraMin}
            eraMax={eraMax} setEraMax={setEraMax}
            origin={origin} setOrigin={setOrigin}
            style={style} setStyle={setStyle}
            renown={renown} setRenown={setRenown}
            keyword={keyword} setKeyword={setKeyword}
            onSubmit={handleSearch}
            isLoading={loading}
          />
        </div>
        
        <div className="mt-10 text-[8px] tracking-[0.4em] text-gray-700 uppercase font-mono">
          Model: 4D Vector Space Mapping
        </div>
      </div>

      {/* Right Panel - Results */}
      <div className="flex-1 relative flex items-center justify-center p-8 md:p-16 z-10 min-h-[60vh] md:min-h-screen">
        <ResultDisplay 
          book={book} 
          loading={loading} 
          error={error} 
          userInputs={{ eraMin, eraMax, origin, style, renown }}
        />
      </div>
    </div>
  );
}

export default App;
