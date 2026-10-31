import tokenStyles from './NounToken.module.css';
import styles from './Legend.module.css';

/** 語の表示の凡例(機能設計書「語の表示」)。色に加えて下線の種類と印で区別する。 */
export function Legend() {
  return (
    <dl className={styles.legend} aria-label="語の表示の凡例">
      <div>
        <dt>
          <span className={tokenStyles.replaced}>語</span>
        </dt>
        <dd>置き換えた語(実線)</dd>
      </div>
      <div>
        <dt>
          <span className={tokenStyles.climbed}>
            語<span className={tokenStyles.mark}>↑</span>
          </span>
        </dt>
        <dd>上の階層から置き換えた語</dd>
      </div>
      <div>
        <dt>
          <span className={tokenStyles.unchanged}>
            語<span className={tokenStyles.mark}>?</span>
          </span>
        </dt>
        <dd>読みが分からず置き換えなかった語</dd>
      </div>
      <div>
        <dt>
          <span className={tokenStyles.unchanged}>
            語<span className={tokenStyles.mark}>・</span>
          </span>
        </dt>
        <dd>兄弟の概念が無く置き換えなかった語</dd>
      </div>
      <div>
        <dt>
          <span className={tokenStyles.notInDictionary}>語</span>
        </dt>
        <dd>辞書に無い語(点線)</dd>
      </div>
    </dl>
  );
}
