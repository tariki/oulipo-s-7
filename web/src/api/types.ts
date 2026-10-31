// APIの型。サーバーのOpenAPI仕様から生成した型(generated/schema.d.ts)に短い名前を付けて公開する。
// 画面のほかの場所は generated/ を直接参照せず、ここから取り込む(手で同じ形の型を書かない)。
import type { components } from './generated/schema';

type Schemas = components['schemas'];

export type TransformRequest = Schemas['TransformRequest'];
export type TransformResponse = Schemas['TransformResponse'];
export type TransformMeta = Schemas['TransformMeta'];
export type Segment = TransformResponse['segments'][number];
export type TextSegment = Schemas['TextSegment'];
export type NounSegment = Schemas['NounSegment'];
export type NounStatus = NounSegment['status'];
export type Mode = TransformRequest['mode'];

export type MetaResponse = Schemas['MetaResponse'];
export type ErrorResponse = Schemas['ErrorResponse'];
export type ErrorCode = Schemas['ErrorBody']['code'];

export type PageViewEvent = Schemas['PageViewEvent'];
export type TransformEvent = Schemas['TransformEvent'];
export type CopyEvent = Schemas['CopyEvent'];
export type AnalyticsEvent = PageViewEvent | TransformEvent | CopyEvent;
