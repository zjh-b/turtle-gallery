const finite = value => typeof value === "number" && Number.isFinite(value);
const validPoint = point => Array.isArray(point) && point.length === 2 && point.every(finite);

export function mirrorPoints(points, count) {
  if (!Number.isInteger(count) || count < 3 || count > 16 || !Array.isArray(points) || !points.every(validPoint)) {
    throw new TypeError("Invalid mirror geometry");
  }
  const result = [];
  for (let index = 0; index < count; index++) {
    const angle = index * Math.PI * 2 / count, c = Math.cos(angle), s = Math.sin(angle);
    for (const mirror of [-1,1]) result.push(points.map(([x,y]) => [x*c-y*mirror*s,x*s+y*mirror*c]));
  }
  return result;
}

function checkedConfig(config) {
  const expected = {version:1,radius:246,min_count:3,max_count:16,max_strokes:60,max_points:2400,max_stroke_points:400};
  if (!config || !Array.isArray(config.view) || config.view.length!==2 || !config.view.every(n=>n===560)
      || Object.entries(expected).some(([key,value])=>config[key]!==value)) throw new TypeError("Invalid kaleidoscope config");
  return Object.freeze({...expected,view:Object.freeze([...config.view])});
}

export class KaleidoscopeModel {
  constructor(config) {
    this.config = checkedConfig(config);
    this.count = 10;
    this.palette = 0;
    this.example();
  }
  _inside(x,y) { return finite(x) && finite(y) && Math.hypot(x,y)<=this.config.radius; }
  _points() { return this.strokes.reduce((total,stroke)=>total+stroke.length,0)+(this.current?.length||0); }
  begin(x,y) {
    if (!this._inside(x,y) || this.current) return false;
    if (this.isExample) this.clear();
    if (this.strokes.length>=this.config.max_strokes || this._points()>=this.config.max_points) {
      this.limitReached=true; return false;
    }
    this.limitReached=false;
    this.current=[[x,y]];
    return true;
  }
  move(x,y) {
    if (!this.current) return false;
    if (!this._inside(x,y)) { this.cancel(); return false; }
    const previous=this.current[this.current.length-1];
    if (Math.hypot(x-previous[0],y-previous[1])<1.5) return false;
    if (this.current.length>=this.config.max_stroke_points || this._points()>=this.config.max_points) {
      this.limitReached=true; return false;
    }
    this.current.push([x,y]);
    return true;
  }
  end() {
    const completed=Boolean(this.current && this.current.length>1);
    if (completed) this.strokes.push(this.current);
    this.current=null;
    return completed;
  }
  cancel() { this.current=null; this.limitReached=false; }
  undo() {
    this.cancel();
    if (this.isExample || !this.strokes.length) return false;
    this.strokes.pop(); return true;
  }
  clear() { this.strokes=[]; this.cancel(); this.isExample=false; }
  setCount(count) {
    if (!Number.isInteger(count) || count<this.config.min_count || count>this.config.max_count) return false;
    this.count=count; return true;
  }
  setPalette(palette) {
    if (!Number.isInteger(palette) || palette<0 || palette>2) return false;
    this.palette=palette; return true;
  }
  example() {
    this.clear();
    this.count=10; this.palette=0;
    const quadratic=(a,b,c,t)=>a.map((value,index)=>(1-t)**2*value+2*(1-t)*t*b[index]+t*t*c[index]);
    for (const [inner,outer,spread,angle] of [[42,239,45,0],[28,190,44,.16],[16,140,36,0],[8,86,24,.16]]) {
      const middle=(inner+outer)/2;
      const points=[];
      for(let i=0;i<=30;i++) points.push(quadratic([inner,0],[middle,-spread],[outer,0],i/30));
      for(let i=1;i<=30;i++) points.push(quadratic([outer,0],[middle,spread],[inner,0],i/30));
      const rotate=([x,y])=>[x*Math.cos(angle)-y*Math.sin(angle),x*Math.sin(angle)+y*Math.cos(angle)];
      this.strokes.push(points.map(rotate));
      this.strokes.push([[inner+5,0],[outer-13,0]].map(rotate));
    }
    this.isExample=true;
  }
}
