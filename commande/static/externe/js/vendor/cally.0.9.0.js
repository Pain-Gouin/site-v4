class le {
  /**
   * @type {T}
   */
  #t;
  #e = /* @__PURE__ */ new Set();
  /**
   * @param {T} current
   */
  constructor(t) {
    this.#t = t;
  }
  /**
   * @return {T}
   */
  get current() {
    return this.#t;
  }
  /**
   * @param {T} value
   */
  set current(t) {
    this.#t != t && ((this.#t = t), this.#e.forEach((n) => n(t)));
  }
  /**
   * @type {import("hooks").Ref["on"]}
   */
  on(t) {
    return this.#e.add(t), () => this.#e.delete(t);
  }
}
const Rt = (e) => new le(e),
  st = Symbol.for("atomico.hooks");
globalThis[st] = globalThis[st] || {};
let A = globalThis[st];
const ue = Symbol.for("Atomico.suspense"),
  Yt = Symbol.for("Atomico.effect"),
  fe = Symbol.for("Atomico.layoutEffect"),
  Ft = Symbol.for("Atomico.insertionEffect"),
  U = (e, t, n) => {
    const { i: s, hooks: o } = A.c,
      r = (o[s] = o[s] || {});
    return (
      (r.value = e(r.value)), (r.effect = t), (r.tag = n), A.c.i++, o[s].value
    );
  },
  It = (e) => U((t = Rt(e)) => t),
  H = () => U((e = Rt(A.c.host)) => e),
  Lt = () => A.c.update,
  de = (e, t, n = 0) => {
    let s = {},
      o = !1;
    const r = () => o,
      a = (l, c) => {
        for (const d in s) {
          const i = s[d];
          i.effect && i.tag === l && (i.value = i.effect(i.value, c));
        }
      };
    return {
      load: (l) => {
        A.c = { host: t, hooks: s, update: e, i: 0, id: n };
        let c;
        try {
          (o = !1), (c = l());
        } catch (d) {
          if (d !== ue) throw d;
          o = !0;
        } finally {
          A.c = null;
        }
        return c;
      },
      cleanEffects: (l) => (
        a(Ft, l),
        () => (
          a(fe, l),
          () => {
            a(Yt, l);
          }
        )
      ),
      isSuspense: r,
    };
  },
  L = Symbol.for;
function xt(e, t) {
  const n = e.length;
  if (n !== t.length) return !1;
  for (let s = 0; s < n; s++) {
    let o = e[s],
      r = t[s];
    if (o !== r) return !1;
  }
  return !0;
}
const T = (e) => typeof e == "function",
  Y = (e) => typeof e == "object",
  { isArray: he } = Array,
  ot = (e, t) =>
    (t ? e instanceof HTMLStyleElement : !0) && "hydrate" in (e?.dataset || {});
function _t(e, t) {
  let n;
  const s = (o) => {
    let { length: r } = o;
    for (let a = 0; a < r; a++) {
      const u = o[a];
      if (u && Array.isArray(u)) s(u);
      else {
        const f = typeof u;
        if (u == null || f === "function" || f === "boolean") continue;
        f === "string" || f === "number"
          ? (n == null && (n = ""), (n += u))
          : (n != null && (t(n), (n = null)), t(u));
      }
    }
  };
  s(e), n != null && t(n);
}
const jt = (e, t, n) => (
  e.addEventListener(t, n), () => e.removeEventListener(t, n)
);
class Bt {
  /**
   *
   * @param {HTMLElement} target
   * @param {string} message
   * @param {string} value
   */
  constructor(t, n, s) {
    (this.message = n), (this.target = t), (this.value = s);
  }
}
class qt extends Bt {}
class me extends Bt {}
const q = "Custom",
  ye = null,
  pe = { true: 1, "": 1, 1: 1 };
function be(e, t, n, s, o) {
  const {
      type: r,
      reflect: a,
      event: u,
      value: f,
      attr: l = ge(t),
    } = n?.name != q && Y(n) && n != ye ? n : { type: n },
    c = r?.name === q && r.map,
    d = f != null ? (r == Function || !T(f) ? () => f : f) : null;
  Object.defineProperty(e, t, {
    configurable: !0,
    /**
     * @this {import("dom").AtomicoThisInternal}
     * @param {any} newValue
     */
    set(i) {
      const m = this[t];
      d && r != Boolean && i == null && (i = d());
      const { error: b, value: g } = (c ? Ee : we)(r, i);
      if (b && g != null)
        throw new qt(
          this,
          `The value defined for prop '${t}' must be of type '${r.name}'`,
          g
        );
      m != g &&
        ((this._props[t] = g ?? void 0),
        this.update(),
        u && zt(this, u),
        this.updated.then(() => {
          a &&
            ((this._ignoreAttr = l),
            De(this, r, l, this[t]),
            (this._ignoreAttr = null));
        }));
    },
    /**
     * @this {import("dom").AtomicoThisInternal}
     */
    get() {
      return this._props[t];
    },
  }),
    d && (o[t] = d()),
    (s[l] = { prop: t, type: r });
}
const zt = (e, { type: t, base: n = CustomEvent, ...s }) =>
    e.dispatchEvent(new n(t, s)),
  ge = (e) => e.replace(/([A-Z])/g, "-$1").toLowerCase(),
  De = (e, t, n, s) =>
    s == null || (t == Boolean && !s)
      ? e.removeAttribute(n)
      : e.setAttribute(
          n,
          t?.name === q && t?.serialize
            ? t?.serialize(s)
            : Y(s)
            ? JSON.stringify(s)
            : t == Boolean
            ? ""
            : s
        ),
  Ce = (e, t) =>
    e == Boolean
      ? !!pe[t]
      : e == Number
      ? Number(t)
      : e == String
      ? t
      : e == Array || e == Object
      ? JSON.parse(t)
      : e.name == q
      ? t
      : // TODO: If when defining reflect the prop can also be of type string?
        new e(t),
  Ee = ({ map: e }, t) => {
    try {
      return { value: e(t), error: !1 };
    } catch {
      return { value: t, error: !0 };
    }
  },
  we = (e, t) =>
    e == null || t == null
      ? { value: t, error: !1 }
      : e != String && t === ""
      ? { value: void 0, error: !1 }
      : e == Object || e == Array || e == Symbol
      ? {
          value: t,
          error: {}.toString.call(t) !== `[object ${e.name}]`,
        }
      : t instanceof e
      ? {
          value: t,
          error: e == Number && Number.isNaN(t.valueOf()),
        }
      : e == String || e == Number || e == Boolean
      ? {
          value: t,
          error:
            e == Number
              ? typeof t != "number"
                ? !0
                : Number.isNaN(t)
              : e == String
              ? typeof t != "string"
              : typeof t != "boolean",
        }
      : { value: t, error: !0 };
let ve = 0;
const Se = (e) => {
    const t = (e?.dataset || {})?.hydrate || "";
    return t || "c" + ve++;
  },
  k = (e, t = HTMLElement) => {
    const n = {},
      s = {},
      o = "prototype" in t && t.prototype instanceof Element,
      r = o ? t : "base" in t ? t.base : HTMLElement,
      { props: a, styles: u } = o ? e : t;
    class f extends r {
      constructor() {
        super(), this._setup(), (this._render = () => e({ ...this._props }));
        for (const c in s) this[c] = s[c];
      }
      /**
       * @returns {import("core").Sheets[]}
       */
      static get styles() {
        return [super.styles, u];
      }
      async _setup() {
        if (this._props) return;
        this._props = {};
        let c, d;
        (this.mounted = new Promise(
          (y) =>
            (this.mount = () => {
              y(),
                c != this.parentNode &&
                  (d != c ? this.unmounted.then(this.update) : this.update()),
                (c = this.parentNode);
            })
        )),
          (this.unmounted = new Promise(
            (y) =>
              (this.unmount = () => {
                y(),
                  (c != this.parentNode || !this.isConnected) &&
                    (i.cleanEffects(!0)()(), (d = this.parentNode), (c = null));
              })
          )),
          (this.symbolId = this.symbolId || Symbol()),
          (this.symbolIdParent = Symbol());
        const i = de(() => this.update(), this, Se(this));
        let m,
          b = !0;
        const g = ot(this);
        (this.update = () => (
          m ||
            ((m = !0),
            (this.updated = (this.updated || this.mounted)
              .then(() => {
                try {
                  const y = i.load(this._render),
                    p = i.cleanEffects();
                  return (
                    y && //@ts-ignore
                      y.render(this, this.symbolId, g),
                    (m = !1),
                    b && !i.isSuspense() && ((b = !1), !g && Te(this)),
                    p()
                  );
                } finally {
                  m = !1;
                }
              })
              .then(
                /**
                 * @param {import("internal/hooks.js").CleanUseEffects} [cleanUseEffect]
                 */
                (y) => {
                  y && y();
                }
              ))),
          this.updated
        )),
          this.update();
      }
      connectedCallback() {
        this.mount(), super.connectedCallback && super.connectedCallback();
      }
      disconnectedCallback() {
        super.disconnectedCallback && super.disconnectedCallback(),
          this.unmount();
      }
      /**
       * @this {import("dom").AtomicoThisInternal}
       * @param {string} attr
       * @param {(string|null)} oldValue
       * @param {(string|null)} value
       */
      attributeChangedCallback(c, d, i) {
        if (n[c]) {
          if (c === this._ignoreAttr || d === i) return;
          const { prop: m, type: b } = n[c];
          try {
            this[m] = Ce(b, i);
          } catch {
            throw new me(
              this,
              `The value defined as attr '${c}' cannot be parsed by type '${b.name}'`,
              i
            );
          }
        } else super.attributeChangedCallback(c, d, i);
      }
      static get props() {
        return { ...super.props, ...a };
      }
      static get observedAttributes() {
        const c = super.observedAttributes || [];
        for (const d in a) be(this.prototype, d, a[d], n, s);
        return Object.keys(n).concat(c);
      }
    }
    return f;
  };
function Te(e) {
  const { styles: t } = e.constructor,
    { shadowRoot: n } = e;
  if (n && t.length) {
    const s = [];
    _t(t, (o) => {
      o && (o instanceof Element ? n.appendChild(o.cloneNode(!0)) : s.push(o));
    }),
      s.length && (n.adoptedStyleSheets = s);
  }
}
const Ht = (e) => (t, n) => {
    U(
      /**
       * Clean the effect hook
       * @type {import("internal/hooks.js").CollectorEffect}
       */
      ([s, o] = []) => (
        (o || !o) &&
          (o && xt(o, n) ? (s = s || !0) : (T(s) && s(), (s = null))),
        [s, n]
      ),
      /**
       * @returns {any}
       */
      ([s, o], r) => (r ? (T(s) && s(), []) : [s || t(), o]),
      e
    );
  },
  I = Ht(Yt),
  Pe = Ht(Ft);
class Wt extends Array {
  /**
   *
   * @param {any} initialState
   * @param {(nextState: any, state:any[], mount: boolean )=>void} mapState
   */
  constructor(t, n) {
    let s = !0;
    const o = (r) => {
      try {
        n(r, this, s);
      } finally {
        s = !1;
      }
    };
    super(void 0, o, n), o(t);
  }
  /**
   * The following code allows a mutable approach to useState
   * and useProp this with the idea of allowing an alternative
   * approach similar to Vue or Qwik of state management
   * @todo pending review with the community
   */
  // get value() {
  //     return this[0];
  // }
  // set value(nextState) {
  //     this[2](nextState, this);
  // }
}
const it = (e) => {
    const t = Lt();
    return U(
      (
        n = new Wt(e, (s, o, r) => {
          (s = T(s) ? s(o[0]) : s), s !== o[0] && ((o[0] = s), r || t());
        })
      ) => n
    );
  },
  S = (e, t) => {
    const [n] = U(
      ([s, o, r = 0] = []) => ((!o || (o && !xt(o, t))) && (s = e()), [s, t, r])
    );
    return n;
  },
  lt = (e) => {
    const { current: t } = H();
    if (!(e in t))
      throw new qt(
        t,
        `For useProp("${e}"), the prop does not exist on the host.`,
        e
      );
    return U(
      (
        n = new Wt(t[e], (s, o) => {
          (s = T(s) ? s(t[e]) : s), (t[e] = s);
        })
      ) => ((n[0] = t[e]), n)
    );
  },
  P = (e, t = {}) => {
    const n = H();
    return (
      n[e] ||
        (n[e] = (s = t.detail) =>
          zt(n.current, {
            type: e,
            ...t,
            detail: s,
          })),
      n[e]
    );
  },
  rt = L("atomico/options");
globalThis[rt] = globalThis[rt] || {
  sheet: !!document.adoptedStyleSheets,
};
const W = globalThis[rt],
  Me = new Promise((e) => {
    W.ssr ||
      (document.readyState === "loading"
        ? jt(document, "DOMContentLoaded", e)
        : e());
  }),
  Ne = {
    checked: 1,
    value: 1,
    selected: 1,
  },
  ke = {
    list: 1,
    type: 1,
    size: 1,
    form: 1,
    width: 1,
    height: 1,
    src: 1,
    href: 1,
    slot: 1,
  },
  Oe = {
    shadowDom: 1,
    staticNode: 1,
    cloneNode: 1,
    children: 1,
    key: 1,
  },
  B = {},
  at = [];
class ct extends Text {}
const Ae = L("atomico/id"),
  F = L("atomico/type"),
  Q = L("atomico/ref"),
  Kt = L("atomico/vnode"),
  Jt = () => {};
function $e(e, t, n) {
  return Xt(this, e, t, n);
}
const Zt = (e, t, ...n) => {
  const s = t || B;
  let { children: o } = s;
  if (((o = o ?? (n.length ? n : at)), e === Jt)) return o;
  const r = e
    ? e instanceof Node
      ? 1
      : //@ts-ignore
        e.prototype instanceof HTMLElement && 2
    : 0;
  if (r === !1 && e instanceof Function)
    return e(o != at ? { children: o, ...s } : s);
  const a = W.render || $e;
  return {
    [F]: Kt,
    type: e,
    props: s,
    children: o,
    key: s.key,
    // key for lists by keys
    // define if the node declares its shadowDom
    shadow: s.shadowDom,
    // allows renderings to run only once
    static: s.staticNode,
    // defines whether the type is a childNode `1` or a constructor `2`
    raw: r,
    // defines whether to use the second parameter for document.createElement
    is: s.is,
    // clone the node if it comes from a reference
    clone: s.cloneNode,
    render: a,
  };
};
function Xt(e, t, n = Ae, s, o) {
  let r;
  if ((t && t[n] && t[n].vnode == e) || e[F] != Kt) return t;
  (e || !t) &&
    ((o = o || e.type == "svg"),
    (r =
      e.type != "host" &&
      (e.raw == 1
        ? (t && e.clone ? t[Q] : t) != e.type
        : e.raw == 2
        ? !(t instanceof e.type)
        : t
        ? t[Q] || t.localName != e.type
        : !t)),
    r &&
      e.type != null &&
      (e.raw == 1 && e.clone
        ? ((s = !0), (t = e.type.cloneNode(!0)), (t[Q] = e.type))
        : (t =
            e.raw == 1
              ? e.type
              : e.raw == 2
              ? new e.type()
              : o
              ? document.createElementNS("http://www.w3.org/2000/svg", e.type)
              : document.createElement(e.type, e.is ? { is: e.is } : void 0))));
  const a = t[n] ? t[n] : B,
    { vnode: u = B, cycle: f = 0 } = a;
  let { fragment: l, handlers: c } = a;
  const { children: d = at, props: i = B } = u;
  if (((c = r ? {} : c || {}), e.static && !r)) return t;
  if (
    (e.shadow &&
      !t.shadowRoot && // @ts-ignore
      t.attachShadow({ mode: "open", ...e.shadow }),
    e.props != i && Ye(t, i, e.props, c, o),
    e.children !== d)
  ) {
    const m = e.shadow ? t.shadowRoot : t;
    l = Re(
      e.children,
      /**
       * @todo for hydration use attribute and send childNodes
       */
      l,
      m,
      n,
      // add support to foreignObject, children will escape from svg
      !f && s,
      o && e.type == "foreignObject" ? !1 : o
    );
  }
  return (t[n] = { vnode: e, handlers: c, fragment: l, cycle: f + 1 }), t;
}
function Ue(e, t) {
  const n = new ct(""),
    s = new ct("");
  let o;
  if ((e[t ? "prepend" : "append"](n), t)) {
    let { lastElementChild: r } = e;
    for (; r; ) {
      const { previousElementSibling: a } = r;
      if (ot(r, !0) && !ot(a, !0)) {
        o = r;
        break;
      }
      r = a;
    }
  }
  return (
    o ? o.before(s) : e.append(s),
    {
      markStart: n,
      markEnd: s,
    }
  );
}
function Re(e, t, n, s, o, r) {
  e = e == null ? null : he(e) ? e : [e];
  const a = t || Ue(n, o),
    { markStart: u, markEnd: f, keyes: l } = a;
  let c;
  const d = l && /* @__PURE__ */ new Set();
  let i = u;
  if (
    (e &&
      _t(e, (m) => {
        if (typeof m == "object" && !m[F]) return;
        const b = m[F] && m.key,
          g = l && b != null && l.get(b);
        i != f && i === g ? d.delete(i) : (i = i == f ? f : i.nextSibling);
        const y = l ? g : i;
        let p = y;
        if (m[F]) p = Xt(m, y, s, o, r);
        else {
          const v = m + "";
          !(p instanceof Text) || p instanceof ct
            ? (p = new Text(v))
            : p.data != v && (p.data = v);
        }
        p != i &&
          (l && d.delete(p),
          !y || l
            ? (n.insertBefore(p, i), l && i != f && d.add(i))
            : y == f
            ? n.insertBefore(p, f)
            : (n.replaceChild(p, y), (i = p))),
          b != null && ((c = c || /* @__PURE__ */ new Map()), c.set(b, p));
      }),
    (i = i == f ? f : i.nextSibling),
    t && i != f)
  )
    for (; i != f; ) {
      const m = i;
      (i = i.nextSibling), m.remove();
    }
  return d && d.forEach((m) => m.remove()), (a.keyes = c), a;
}
function Ye(e, t, n, s, o) {
  for (const r in t) !(r in n) && Tt(e, r, t[r], null, o, s);
  for (const r in n) Tt(e, r, t[r], n[r], o, s);
}
function Tt(e, t, n, s, o, r) {
  if (
    ((t = t == "class" && !o ? "className" : t),
    (n = n ?? null),
    (s = s ?? null),
    t in e && Ne[t] && (n = e[t]),
    !(s === n || Oe[t] || t[0] == "_"))
  )
    if (e.localName === "slot" && t === "assignNode" && "assign" in e)
      e.assign(s);
    else if (t[0] == "o" && t[1] == "n" && (T(s) || T(n)))
      Fe(e, t.slice(2), s, r);
    else if (t == "ref") s && (T(s) ? s(e) : (s.current = e));
    else if (t == "style") {
      const { style: a } = e;
      (n = n || ""), (s = s || "");
      const u = Y(n),
        f = Y(s);
      if (u)
        for (const l in n)
          if (f) !(l in s) && Pt(a, l, null);
          else break;
      if (f)
        for (const l in s) {
          const c = s[l];
          (u && n[l] === c) || Pt(a, l, c);
        }
      else a.cssText = s;
    } else {
      const a = t[0] == "$" ? t.slice(1) : t;
      a === t && ((!o && !ke[t] && t in e) || T(s) || T(n))
        ? (e[t] = s ?? "")
        : s == null
        ? e.removeAttribute(a)
        : e.setAttribute(a, Y(s) ? JSON.stringify(s) : s);
    }
}
function Fe(e, t, n, s) {
  if ((s.handleEvent || (s.handleEvent = (o) => s[o.type].call(e, o)), n)) {
    if (!s[t]) {
      const o = n.capture || n.once || n.passive ? Object.assign({}, n) : null;
      e.addEventListener(t, s, o);
    }
    s[t] = n;
  } else s[t] && (e.removeEventListener(t, s), delete s[t]);
}
function Pt(e, t, n) {
  let s = "setProperty";
  n == null && ((s = "removeProperty"), (n = null)),
    ~t.indexOf("-") ? e[s](t, n) : (e[t] = n);
}
const Ie = Zt("host", { style: "display: contents" }),
  Gt = "value",
  Le = (e, t) => {
    const n = H(),
      s = It();
    Pe(
      () =>
        jt(
          n.current,
          "ConnectContext",
          /**
           * @param {CustomEvent<import("context").DetailConnectContext>} event
           */
          (o) => {
            o.composedPath().at(0) !== o.currentTarget &&
              e === o.detail.id &&
              (o.stopPropagation(), o.detail.connect(s));
          }
        ),
      [e]
    ),
      (s.current = t);
  },
  ut = (e) => {
    const t = P("ConnectContext", {
        bubbles: !0,
        composed: !0,
      }),
      [n, s] = it(() => {
        if (W.ssr) return;
        let r;
        return (
          t({
            id: e,
            /**
             * @param {import("core").Ref} parentContext
             */
            connect(a) {
              r = a;
            },
          }),
          r
        );
      }),
      o = Lt();
    return (
      I(() => {
        Me.then(() =>
          t({
            id: e,
            connect: s,
          })
        );
      }, [e]),
      I(() => {
        if (n) return n.on(o);
      }, [n]),
      n?.current || e[Gt]
    );
  },
  Qt = (e) => {
    const t = k(({ value: n }) => (Le(t, n), Ie), {
      props: {
        value: {
          type: Object,
          value: () => e,
        },
      },
    });
    return (t[Gt] = e), t;
  };
Qt({
  /**
   *
   * @param {string} type
   * @param {string} id
   */
  dispatch(e, t) {},
});
const Mt = {};
function K(e, ...t) {
  const n = (e.raw || e).reduce((s, o, r) => s + o + (t[r] || ""), "");
  return (Mt[n] = Mt[n] || xe(n));
}
function xe(e) {
  if (W.sheet) {
    const t = new CSSStyleSheet();
    return t.replaceSync(e), t;
  } else {
    const t = document.createElement("style");
    return (t.textContent = e), t;
  }
}
const h = (e, t, n) => (t == null ? (t = { key: n }) : (t.key = n), Zt(e, t)),
  M = h,
  ft = K`*,*:before,*:after{box-sizing:border-box}button{padding:0;touch-action:manipulation;cursor:pointer;user-select:none}`,
  dt = K`.vh{position:absolute;transform:scale(0)}`;
function ht() {
  const e = /* @__PURE__ */ new Date();
  return new C(e.getFullYear(), e.getMonth() + 1, e.getDate());
}
const _e = 864e5;
function je(e) {
  const t = w(e);
  t.setDate(t.getUTCDate() + 3 - ((t.getUTCDay() + 6) % 7));
  const n = new Date(t.getUTCFullYear(), 0, 4);
  return (
    1 +
    Math.round(
      ((t.getTime() - n.getTime()) / _e - 3 + ((n.getUTCDay() + 6) % 7)) / 7
    )
  );
}
function mt(e, t = 0) {
  const n = w(e),
    s = n.getUTCDay(),
    o = (s < t ? 7 : 0) + s - t;
  return n.setUTCDate(n.getUTCDate() - o), C.from(n);
}
function Vt(e, t = 0) {
  return mt(e, t).add({ days: 6 });
}
function te(e) {
  return C.from(new Date(Date.UTC(e.year, e.month, 0)));
}
function J(e, t, n) {
  return t && C.compare(e, t) < 0 ? t : n && C.compare(e, n) > 0 ? n : e;
}
const Be = { days: 1 };
function qe(e, t = 0) {
  let n = mt(e.toPlainDate(), t);
  const s = Vt(te(e), t),
    o = [];
  for (; C.compare(n, s) < 0; ) {
    const r = [];
    for (let a = 0; a < 7; a++) r.push(n), (n = n.add(Be));
    o.push(r);
  }
  return o;
}
function w(e) {
  return new Date(Date.UTC(e.year, e.month - 1, e.day ?? 1));
}
const ze = /^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[0-1])$/,
  V = (e, t) => e.toString().padStart(t, "0");
class C {
  constructor(t, n, s) {
    (this.year = t), (this.month = n), (this.day = s);
  }
  // this is an incomplete implementation that only handles arithmetic on a single unit at a time.
  // i didn't want to get into more complex arithmetic since it get tricky fast
  // this is enough to serve my needs and will still be a drop-in replacement when actual Temporal API lands
  add(t) {
    const n = w(this);
    if ("days" in t) return n.setUTCDate(this.day + t.days), C.from(n);
    let { year: s, month: o } = this;
    "months" in t
      ? ((o = this.month + t.months), n.setUTCMonth(o - 1))
      : ((s = this.year + t.years), n.setUTCFullYear(s));
    const r = C.from(w({ year: s, month: o, day: 1 }));
    return J(C.from(n), r, te(r));
  }
  toString() {
    return `${V(this.year, 4)}-${V(this.month, 2)}-${V(this.day, 2)}`;
  }
  toPlainYearMonth() {
    return new Z(this.year, this.month);
  }
  equals(t) {
    return C.compare(this, t) === 0;
  }
  static compare(t, n) {
    return t.year < n.year
      ? -1
      : t.year > n.year
      ? 1
      : t.month < n.month
      ? -1
      : t.month > n.month
      ? 1
      : t.day < n.day
      ? -1
      : t.day > n.day
      ? 1
      : 0;
  }
  static from(t) {
    if (typeof t == "string") {
      const n = t.match(ze);
      if (!n) throw new TypeError(t);
      const [, s, o, r] = n;
      return new C(parseInt(s, 10), parseInt(o, 10), parseInt(r, 10));
    }
    return new C(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate());
  }
}
class Z {
  constructor(t, n) {
    (this.year = t), (this.month = n);
  }
  add(t) {
    const n = w(this),
      s = (t.months ?? 0) + (t.years ?? 0) * 12;
    return (
      n.setUTCMonth(n.getUTCMonth() + s),
      new Z(n.getUTCFullYear(), n.getUTCMonth() + 1)
    );
  }
  equals(t) {
    return this.year === t.year && this.month === t.month;
  }
  toPlainDate() {
    return new C(this.year, this.month, 1);
  }
}
function z(e, t) {
  if (t)
    try {
      return e.from(t);
    } catch {}
}
function N(e) {
  const [t, n] = lt(e);
  return [S(() => z(C, t), [t]), (r) => n(r?.toString())];
}
function He(e) {
  const [t = "", n] = lt(e);
  return [
    S(() => {
      const [r, a] = t.split("/"),
        u = z(C, r),
        f = z(C, a);
      return u && f ? [u, f] : [];
    }, [t]),
    (r) => n(`${r[0]}/${r[1]}`),
  ];
}
function We(e) {
  const [t = "", n] = lt(e);
  return [
    S(() => {
      const r = [];
      for (const a of t.trim().split(/\s+/)) {
        const u = z(C, a);
        u && r.push(u);
      }
      return r;
    }, [t]),
    (r) => n(r.join(" ")),
  ];
}
function $(e, t) {
  return S(() => new Intl.DateTimeFormat(t, { timeZone: "UTC", ...e }), [t, e]);
}
function Nt(e, t, n) {
  const s = $(e, n);
  return S(() => {
    const o = [],
      r = /* @__PURE__ */ new Date();
    for (var a = 0; a < 7; a++) {
      const u = (r.getUTCDay() - t + 7) % 7;
      (o[u] = s.format(r)), r.setUTCDate(r.getUTCDate() + 1);
    }
    return o;
  }, [t, s]);
}
const kt = (e, t, n) => J(e, t, n) === e,
  Ot = (e) => e.target.matches(":dir(ltr)"),
  Ke = { month: "long", day: "numeric" },
  Je = { month: "long" },
  Ze = { weekday: "long" },
  tt = { bubbles: !0 };
function Xe({ props: e, context: t }) {
  const { offset: n } = e,
    {
      firstDayOfWeek: s,
      isDateDisallowed: o,
      min: r,
      max: a,
      today: u,
      page: f,
      locale: l,
      focusedDate: c,
      formatWeekday: d,
    } = t,
    i = u ?? ht(),
    m = Nt(Ze, s, l),
    b = S(() => ({ weekday: d }), [d]),
    g = Nt(b, s, l),
    y = $(Ke, l),
    p = $(Je, l),
    v = S(() => f.start.add({ months: n }), [f, n]),
    X = S(() => qe(v, s), [v, s]),
    se = P("focusday", tt),
    oe = P("selectday", tt),
    re = P("hoverday", tt);
  function Dt(D) {
    se(J(D, r, a));
  }
  function ae(D) {
    let E;
    switch (D.key) {
      case "ArrowRight":
        E = c.add({ days: Ot(D) ? 1 : -1 });
        break;
      case "ArrowLeft":
        E = c.add({ days: Ot(D) ? -1 : 1 });
        break;
      case "ArrowDown":
        E = c.add({ days: 7 });
        break;
      case "ArrowUp":
        E = c.add({ days: -7 });
        break;
      case "PageUp":
        E = c.add(D.shiftKey ? { years: -1 } : { months: -1 });
        break;
      case "PageDown":
        E = c.add(D.shiftKey ? { years: 1 } : { months: 1 });
        break;
      case "Home":
        E = mt(c, s);
        break;
      case "End":
        E = Vt(c, s);
        break;
      default:
        return;
    }
    Dt(E), D.preventDefault();
  }
  function ce(D) {
    const E = v.equals(D);
    if (!t.showOutsideDays && !E) return;
    const ie = D.equals(c),
      Ct = D.equals(i),
      _ = w(D),
      j = o?.(_),
      Et = !kt(D, r, a);
    let wt = "",
      O;
    if (t.type === "range") {
      const [R, G] = t.value,
        vt = R?.equals(D),
        St = G?.equals(D);
      (O = R && G && kt(D, R, G)),
        (wt = `${vt ? "range-start" : ""} ${St ? "range-end" : ""} ${
          O && !vt && !St ? "range-inner" : ""
        }`);
    } else
      t.type === "multi"
        ? (O = t.value.some((R) => R.equals(D)))
        : (O = t.value?.equals(D));
    return {
      part: `${`button day day-${_.getDay()} ${
        // we don't want outside days to ever be shown as selected
        E ? (O ? "selected" : "") : "outside"
      } ${j ? "disallowed" : ""} ${Ct ? "today" : ""} ${
        t.getDayParts?.(_) ?? ""
      }`} ${wt}`,
      tabindex: E && ie ? 0 : -1,
      disabled: Et,
      "aria-disabled": j ? "true" : void 0,
      "aria-pressed": E && O,
      "aria-current": Ct ? "date" : void 0,
      "aria-label": y.format(_),
      onkeydown: ae,
      onclick() {
        j || oe(D), Dt(D);
      },
      onmouseover() {
        !j && !Et && re(D);
      },
    };
  }
  return {
    weeks: X,
    yearMonth: v,
    daysLong: m,
    daysVisible: g,
    formatter: p,
    getDayProps: ce,
  };
}
const et = ht(),
  x = Qt({
    type: "date",
    firstDayOfWeek: 1,
    focusedDate: et,
    page: { start: et.toPlainYearMonth(), end: et.toPlainYearMonth() },
  });
customElements.define("calendar-ctx", x);
const Ge = (e, t) => (t + e) % 7,
  Qe = k(
    (e) => {
      const t = ut(x),
        n = It(),
        s = Xe({ props: e, context: t });
      function o() {
        n.current.querySelector("button[tabindex='0']")?.focus();
      }
      return /* @__PURE__ */ M("host", {
        shadowDom: !0,
        focus: o,
        children: [
          /* @__PURE__ */ h("div", {
            id: "h",
            part: "heading",
            children: s.formatter.format(w(s.yearMonth)),
          }),
          /* @__PURE__ */ M("table", {
            ref: n,
            "aria-labelledby": "h",
            part: "table",
            children: [
              /* @__PURE__ */ M("colgroup", {
                children: [
                  t.showWeekNumbers &&
                    /* @__PURE__ */ h("col", { part: "col-weeknumber" }),
                  /* @__PURE__ */ h("col", { part: "col-1" }),
                  /* @__PURE__ */ h("col", { part: "col-2" }),
                  /* @__PURE__ */ h("col", { part: "col-3" }),
                  /* @__PURE__ */ h("col", { part: "col-4" }),
                  /* @__PURE__ */ h("col", { part: "col-5" }),
                  /* @__PURE__ */ h("col", { part: "col-6" }),
                  /* @__PURE__ */ h("col", { part: "col-7" }),
                ],
              }),
              /* @__PURE__ */ h("thead", {
                children: /* @__PURE__ */ M("tr", {
                  part: "tr head",
                  children: [
                    t.showWeekNumbers &&
                      /* @__PURE__ */ h("th", {
                        part: "th weeknumber",
                        children: /* @__PURE__ */ h("slot", {
                          name: "weeknumber",
                          children: /* @__PURE__ */ h("span", {
                            "aria-label": "Week",
                            children: "#",
                          }),
                        }),
                      }),
                    s.daysLong.map((r, a) =>
                      /* @__PURE__ */ M("th", {
                        part: `th day day-${Ge(t.firstDayOfWeek, a)}`,
                        scope: "col",
                        children: [
                          /* @__PURE__ */ h("span", {
                            class: "vh",
                            children: r,
                          }),
                          /* @__PURE__ */ h("span", {
                            "aria-hidden": "true",
                            children: s.daysVisible[a],
                          }),
                        ],
                      })
                    ),
                  ],
                }),
              }),
              /* @__PURE__ */ h("tbody", {
                children: s.weeks.map((r, a) =>
                  /* @__PURE__ */ M(
                    "tr",
                    {
                      part: "tr week",
                      children: [
                        t.showWeekNumbers &&
                          /* @__PURE__ */ h("th", {
                            class: "num",
                            part: "th weeknumber",
                            scope: "row",
                            children: je(r[0]),
                          }),
                        r.map((u, f) => {
                          const l = s.getDayProps(u);
                          return /* @__PURE__ */ h(
                            "td",
                            {
                              part: "td",
                              children:
                                l &&
                                /* @__PURE__ */ h("button", {
                                  class: "num",
                                  ...l,
                                  children: u.day,
                                }),
                            },
                            f
                          );
                        }),
                      ],
                    },
                    a
                  )
                ),
              }),
            ],
          }),
        ],
      });
    },
    {
      props: {
        offset: {
          type: Number,
          value: 0,
        },
      },
      styles: [
        ft,
        dt,
        K`:host{--color-accent: black;--color-text-on-accent: white;display:flex;flex-direction:column;gap:.25rem;text-align:center;inline-size:fit-content}table{border-collapse:collapse;font-size:.875rem}th{inline-size:2.25rem;block-size:2.25rem}td{padding-inline:0}.num{font-variant-numeric:tabular-nums}button{color:inherit;font-size:inherit;background:transparent;border:0;block-size:2.25rem;inline-size:2.25rem}button:hover:where(:not(:disabled,[aria-disabled])){background:#0000000d}button:is([aria-pressed=true],:focus-visible){background:var(--color-accent);color:var(--color-text-on-accent)}button:focus-visible{outline:1px solid var(--color-text-on-accent);outline-offset:-2px}button:disabled,:host::part(outside),:host::part(disallowed){cursor:default;opacity:.5}`,
      ],
    }
  );
customElements.define("calendar-month", Qe);
function At(e) {
  return /* @__PURE__ */ h("button", {
    part: `button ${e.name} ${e.onclick ? "" : "disabled"}`,
    onclick: e.onclick,
    "aria-disabled": e.onclick ? null : "true",
    children: /* @__PURE__ */ h("slot", { name: e.name, children: e.children }),
  });
}
function yt(e) {
  const t = w(e.page.start),
    n = w(e.page.end);
  return /* @__PURE__ */ h(x, {
    value: e,
    onselectday: e.onSelect,
    onfocusday: e.onFocus,
    onhoverday: e.onHover,
    children: /* @__PURE__ */ M("div", {
      role: "group",
      "aria-labelledby": "h",
      part: "container",
      children: [
        /* @__PURE__ */ h("div", {
          id: "h",
          class: "vh",
          "aria-live": "polite",
          "aria-atomic": "true",
          children: e.formatVerbose.formatRange(t, n),
        }),
        /* @__PURE__ */ M("div", {
          part: "header",
          children: [
            /* @__PURE__ */ h(At, {
              name: "previous",
              onclick: e.previous,
              children: "Previous",
            }),
            /* @__PURE__ */ h("slot", {
              part: "heading",
              name: "heading",
              children: /* @__PURE__ */ h("div", {
                "aria-hidden": "true",
                children: e.format.formatRange(t, n),
              }),
            }),
            /* @__PURE__ */ h(At, {
              name: "next",
              onclick: e.next,
              children: "Next",
            }),
          ],
        }),
        /* @__PURE__ */ h("slot", { part: "months" }),
      ],
    }),
  });
}
const pt = {
    value: {
      type: String,
      value: "",
    },
    min: {
      type: String,
      value: "",
    },
    max: {
      type: String,
      value: "",
    },
    today: {
      type: String,
      value: "",
    },
    isDateDisallowed: {
      type: Function,
      value: (e) => !1,
    },
    formatWeekday: {
      type: String,
      value: () => "narrow",
    },
    getDayParts: {
      type: Function,
      value: (e) => "",
    },
    firstDayOfWeek: {
      type: Number,
      value: () => 1,
    },
    showOutsideDays: {
      type: Boolean,
      value: !1,
    },
    locale: {
      type: String,
      value: () => {},
    },
    months: {
      type: Number,
      value: 1,
    },
    focusedDate: {
      type: String,
      value: () => {},
    },
    pageBy: {
      type: String,
      value: () => "months",
    },
    showWeekNumbers: {
      type: Boolean,
      value: !1,
    },
  },
  bt = [
    ft,
    dt,
    K`:host{display:block;inline-size:fit-content}:host::part(container){display:flex;flex-direction:column;gap:1em}:host::part(header){display:flex;align-items:center;justify-content:space-between}:host::part(heading){font-weight:700;font-size:1.25em}:host::part(button){display:flex;align-items:center;justify-content:center}:host::part(button disabled){cursor:default;opacity:.5}`,
  ],
  Ve = { year: "numeric" },
  tn = { year: "numeric", month: "long" };
function nt(e, t) {
  return (t.year - e.year) * 12 + t.month - e.month;
}
const $t = (e, t) => (
  (e = t === 12 ? new Z(e.year, 1) : e),
  {
    start: e,
    end: e.add({ months: t - 1 }),
  }
);
function en({ pageBy: e, focusedDate: t, months: n, max: s, min: o, goto: r }) {
  const a = e === "single" ? 1 : n,
    [u, f] = it(() => $t(t.toPlainYearMonth(), n)),
    l = (d) => f($t(u.start.add({ months: d }), n)),
    c = (d) => {
      const i = nt(u.start, d.toPlainYearMonth());
      return i >= 0 && i < n;
    };
  return (
    I(() => {
      if (c(t)) return;
      const d = nt(t.toPlainYearMonth(), u.start);
      r(t.add({ months: d }));
    }, [u.start]),
    I(() => {
      if (c(t)) return;
      const d = nt(u.start, t.toPlainYearMonth());
      l(d === -1 ? -a : d === n ? a : Math.floor(d / n) * n);
    }, [t, a, n]),
    {
      page: u,
      previous: !o || !c(o) ? () => l(-a) : void 0,
      next: !s || !c(s) ? () => l(a) : void 0,
    }
  );
}
function gt({
  months: e,
  pageBy: t,
  locale: n,
  focusedDate: s,
  setFocusedDate: o,
}) {
  const [r] = N("min"),
    [a] = N("max"),
    [u] = N("today"),
    f = P("focusday"),
    l = P("change"),
    c = S(() => J(s ?? u ?? ht(), r, a), [s, u, r, a]);
  function d(p) {
    o(p), f(w(p));
  }
  const {
      next: i,
      previous: m,
      page: b,
    } = en({
      pageBy: t,
      focusedDate: c,
      months: e,
      min: r,
      max: a,
      goto: d,
    }),
    g = H();
  function y(p) {
    const v = p?.target ?? "day";
    v === "day"
      ? g.current.querySelectorAll("calendar-month").forEach((X) => X.focus(p))
      : g.current.shadowRoot.querySelector(`[part~='${v}']`).focus(p);
  }
  return {
    format: $(Ve, n),
    formatVerbose: $(tn, n),
    page: b,
    focusedDate: c,
    dispatch: l,
    onFocus(p) {
      p.stopPropagation(), d(p.detail), setTimeout(y);
    },
    min: r,
    max: a,
    today: u,
    next: i,
    previous: m,
    focus: y,
  };
}
const nn = k(
  (e) => {
    const [t, n] = N("value"),
      [s = t, o] = N("focusedDate"),
      r = gt({
        ...e,
        focusedDate: s,
        setFocusedDate: o,
      });
    function a(u) {
      n(u.detail), r.dispatch();
    }
    return /* @__PURE__ */ h("host", {
      shadowDom: !0,
      focus: r.focus,
      children: /* @__PURE__ */ h(yt, {
        ...e,
        ...r,
        type: "date",
        value: t,
        onSelect: a,
      }),
    });
  },
  { props: pt, styles: bt }
);
customElements.define("calendar-date", nn);
function ee(e) {
  return /* @__PURE__ */ M(Jt, {
    children: [
      /* @__PURE__ */ h("label", {
        part: "label",
        for: "s",
        children: /* @__PURE__ */ h("slot", {
          name: "label",
          children: e.label,
        }),
      }),
      /* @__PURE__ */ h("select", {
        id: "s",
        part: "select",
        onchange: e.onChange,
        children: e.options.map((t) =>
          /* @__PURE__ */ h("option", { part: "option", ...t })
        ),
      }),
    ],
  });
}
const ne = [ft, dt];
function sn(e, t) {
  return Array.from({ length: e }, (n, s) => t(s));
}
function on(e) {
  const { min: t, max: n, focusedDate: s } = ut(x),
    o = P("focusday", { bubbles: !0 }),
    r = s.toPlainYearMonth(),
    a = r.year,
    u = Math.floor(e.maxYears / 2),
    f = a - u,
    l = a + (e.maxYears - u - 1),
    c = Math.max(f, t?.year ?? -1 / 0),
    d = Math.min(l, n?.year ?? 1 / 0),
    i = sn(d - c + 1, (b) => {
      const g = c + b;
      return {
        label: `${g}`,
        value: `${g}`,
        selected: g === r.year,
      };
    });
  function m(b) {
    const y = parseInt(b.currentTarget.value) - r.year;
    o(s.add({ years: y }));
  }
  return { options: i, onChange: m };
}
const rn = k(
  (e) => {
    const t = on(e);
    return /* @__PURE__ */ h("host", {
      shadowDom: !0,
      children: /* @__PURE__ */ h(ee, { label: "Year", ...t }),
    });
  },
  {
    props: {
      maxYears: { type: Number, value: 20 },
    },
    styles: ne,
  }
);
customElements.define("calendar-select-year", rn);
function an(e) {
  const { min: t, max: n, focusedDate: s, locale: o } = ut(x),
    r = P("focusday", { bubbles: !0 }),
    a = S(() => ({ month: e.formatMonth }), [e.formatMonth]),
    u = $(a, o),
    f = S(() => {
      const i = [],
        m = /* @__PURE__ */ new Date();
      for (var b = 0; b < 12; b++) {
        const g = (m.getUTCMonth() + 12) % 12;
        (i[g] = u.format(m)), m.setUTCMonth(m.getUTCMonth() + 1);
      }
      return i;
    }, [u]),
    l = s.toPlainYearMonth(),
    c = f.map((i, m) => {
      const b = m + 1,
        g = l.add({ months: b - l.month }).toPlainDate(),
        y =
          (t != null && C.compare(g, t) < 0) ||
          (n != null && C.compare(g, n) > 0);
      return {
        label: i,
        value: `${b}`,
        disabled: y,
        selected: b === l.month,
      };
    });
  function d(i) {
    const b = parseInt(i.currentTarget.value) - l.month;
    r(s.add({ months: b }));
  }
  return { options: c, onChange: d };
}
const cn = k(
  (e) => {
    const t = an(e);
    return /* @__PURE__ */ h("host", {
      shadowDom: !0,
      children: /* @__PURE__ */ h(ee, { label: "Month", ...t }),
    });
  },
  {
    props: {
      formatMonth: {
        type: String,
        value: () => "long",
      },
    },
    styles: ne,
  }
);
customElements.define("calendar-select-month", cn);
const Ut = (e, t) => (C.compare(e, t) < 0 ? [e, t] : [t, e]),
  ln = k(
    (e) => {
      const [t, n] = He("value"),
        [s = t[0], o] = N("focusedDate"),
        r = gt({
          ...e,
          focusedDate: s,
          setFocusedDate: o,
        }),
        a = P("rangestart"),
        u = P("rangeend"),
        [f, l] = N("tentative"),
        [c, d] = it();
      I(() => d(void 0), [f]);
      function i(y) {
        r.onFocus(y), m(y);
      }
      function m(y) {
        y.stopPropagation(), f && d(y.detail);
      }
      function b(y) {
        const p = y.detail;
        y.stopPropagation(),
          f ? (n(Ut(f, p)), l(void 0), u(w(p)), r.dispatch()) : (l(p), a(w(p)));
      }
      const g = f ? Ut(f, c ?? f) : t;
      return /* @__PURE__ */ h("host", {
        shadowDom: !0,
        focus: r.focus,
        children: /* @__PURE__ */ h(yt, {
          ...e,
          ...r,
          type: "range",
          value: g,
          onFocus: i,
          onHover: m,
          onSelect: b,
        }),
      });
    },
    {
      props: {
        ...pt,
        tentative: {
          type: String,
          value: "",
        },
      },
      styles: bt,
    }
  );
customElements.define("calendar-range", ln);
const un = k(
  (e) => {
    const [t, n] = We("value"),
      [s = t[0], o] = N("focusedDate"),
      r = gt({
        ...e,
        focusedDate: s,
        setFocusedDate: o,
      });
    function a(u) {
      const f = [...t],
        l = t.findIndex((c) => c.equals(u.detail));
      l < 0 ? f.push(u.detail) : f.splice(l, 1), n(f), r.dispatch();
    }
    return /* @__PURE__ */ h("host", {
      shadowDom: !0,
      focus: r.focus,
      children: /* @__PURE__ */ h(yt, {
        ...e,
        ...r,
        type: "multi",
        value: t,
        onSelect: a,
      }),
    });
  },
  { props: pt, styles: bt }
);
customElements.define("calendar-multi", un);
export {
  nn as CalendarDate,
  Qe as CalendarMonth,
  un as CalendarMulti,
  ln as CalendarRange,
  cn as CalendarSelectMonth,
  rn as CalendarSelectYear,
};
