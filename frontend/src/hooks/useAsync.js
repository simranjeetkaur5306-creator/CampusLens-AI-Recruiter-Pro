import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../services/api";

// Runs an async function on mount (and when deps change). Ignores stale results.
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const fnRef = useRef(fn);
  const counter = useRef(0);

  useEffect(() => {
    fnRef.current = fn;
  });

  useEffect(() => () => { counter.current += 1; }, []);

  const run = useCallback(async () => {
    const id = ++counter.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fnRef.current();
      if (id === counter.current) setState({ data, loading: false, error: null });
    } catch (err) {
      if (id === counter.current) setState({ data: null, loading: false, error: errorMessage(err) });
    }
  }, []);

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ...state, reload: run };
}