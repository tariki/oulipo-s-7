import type { ConceptRef, ConceptRoute, GojuonRoute, Route } from '../api/types';
import styles from './RoutePanel.module.css';

interface RoutePanelProps {
  route: Route;
  original: string;
  replaced: string;
}

/** 経路の間の語を、3語目と4語目の間で省いたことを示す位置(機能設計書「経路の間の語」)。 */
const OMISSION_AT = 3;

const RELATION_LABELS = {
  hypernym: '上位語',
  instance_hypernym: 'インスタンスの上位語',
} as const;

/** 置換経路([P1: F6])。五十音順なら前後の見出し語、概念版なら通った概念と関係の種類。 */
export function RoutePanel({ route, original, replaced }: RoutePanelProps) {
  return (
    <div className={styles.route}>
      <h3 className={styles.heading}>置き換えの経路</h3>
      {route.type === 'gojuon' ? (
        <GojuonRouteView route={route} original={original} replaced={replaced} />
      ) : (
        <ConceptRouteView route={route} />
      )}
    </div>
  );
}

function GojuonRouteView({
  route,
  original,
  replaced,
}: {
  route: GojuonRoute;
  original: string;
  replaced: string;
}) {
  const before =
    route.neighborsOmitted > 0 ? route.neighbors.slice(0, OMISSION_AT) : route.neighbors;
  const after = route.neighborsOmitted > 0 ? route.neighbors.slice(OMISSION_AT) : [];
  return (
    <>
      <p className={styles.note}>五十音順の辞書で、元の語から順に進んだ語です。</p>
      <ol className={styles.chain}>
        <li className={styles.end}>
          {original}
          <span className={styles.position}>(元の語)</span>
        </li>
        {before.map((word, i) => (
          <li key={`before-${String(i)}`}>{word}</li>
        ))}
        {route.neighborsOmitted > 0 && (
          <li className={styles.omitted}>
            …({route.neighborsOmitted.toLocaleString('ja-JP')}語省略)
          </li>
        )}
        {after.map((word, i) => (
          <li key={`after-${String(i)}`}>{word}</li>
        ))}
        <li className={styles.end}>
          {replaced}
          <span className={styles.position}>(変換後の語)</span>
        </li>
      </ol>
      {route.wrapped && <p className={styles.note}>辞書の末尾を超えたため、先頭に戻りました。</p>}
    </>
  );
}

function ConceptRouteView({ route }: { route: ConceptRoute }) {
  return (
    <>
      {route.climbs.length > 0 && (
        <>
          <p className={styles.note}>兄弟の概念が無いため、階層を上がりました。</p>
          <ol className={styles.steps}>
            {route.climbs.map((step, i) => (
              <li key={i}>
                <ConceptLabel concept={step.from} />
                <span className={styles.relation}>→ {RELATION_LABELS[step.relation]} →</span>
                <ConceptLabel concept={step.to} />
                {step.to.definition !== null && (
                  <span className={styles.stepDefinition}>{step.to.definition}</span>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
      <dl className={styles.concepts}>
        <div>
          <dt>兄弟の概念の共通の上位語</dt>
          <dd>
            <ConceptView concept={route.parent} />
          </dd>
        </div>
        <div>
          <dt>{route.climbs.length > 0 ? '上がった先の概念' : '元の概念'}</dt>
          <dd>
            <ConceptView concept={route.from} />
          </dd>
        </div>
        <div>
          <dt>変換後の概念(兄弟{route.groupSize.toLocaleString('ja-JP')}個の中で進んだ先)</dt>
          <dd>
            <ConceptView concept={route.to} />
          </dd>
        </div>
      </dl>
      {route.wrapped && (
        <p className={styles.note}>兄弟の概念の末尾を超えたため、先頭に戻りました。</p>
      )}
    </>
  );
}

function ConceptLabel({ concept }: { concept: ConceptRef }) {
  return <span className={styles.concept}>{concept.lemma ?? '(日本語の見出し語なし)'}</span>;
}

function ConceptView({ concept }: { concept: ConceptRef }) {
  return (
    <>
      <ConceptLabel concept={concept} />
      {concept.definition !== null && (
        <span className={styles.definition}>{concept.definition}</span>
      )}
    </>
  );
}
