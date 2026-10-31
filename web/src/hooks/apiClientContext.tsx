import { type ReactNode, createContext, useContext } from 'react';

import { ApiClient } from '../api/ApiClient';

const defaultClient = new ApiClient();
const ApiClientContext = createContext<ApiClient>(defaultClient);

interface ApiClientProviderProps {
  client: ApiClient;
  children: ReactNode;
}

/** 画面が使う ApiClient を差し替える(テストで偽物を渡す)。 */
export function ApiClientProvider({ client, children }: ApiClientProviderProps) {
  return <ApiClientContext value={client}>{children}</ApiClientContext>;
}

/** 画面が使う ApiClient。pages/ は api/ を直接取り込めないため、ここから受け取る。 */
export function useApiClient(): ApiClient {
  return useContext(ApiClientContext);
}
