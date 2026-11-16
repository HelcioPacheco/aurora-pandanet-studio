const assert=require('node:assert/strict');
const {grid}=require('./static/output-layout.js');
// Four boards on a wide canvas must improve on the old 2x2/163px output.
const wide=grid(4,1244,604);
assert.equal(wide.cols,4);assert.ok(wide.boardSize>=300);
// Portrait output benefits from stacking rather than reusing the wide layout.
const portrait=grid(4,560,1450);
assert.ok(portrait.cols<wide.cols);assert.ok(portrait.boardSize>200);
for(const [width,height] of [[1244,604],[1884,964],[560,1450],[360,540]]){
 for(let count=1;count<=16;count++){
  const g=grid(count,width,height);
  assert.ok(g.cols*g.rows>=count);
  assert.ok(g.cols*g.boardSize+(g.cols-1)*12<=width);
  assert.ok(g.rows*(g.boardSize+64)+(g.rows-1)*12<=height);
 }
}
assert.equal(grid(1,1200,700).boardSize,636);
console.log('Equal-sized OBS boards fit landscape and portrait canvases.');

for(const caption of [64,86])for(const count of [1,4,9,16]){
 const g=grid(count,1244,604,12,caption);assert.ok(g.rows*(g.boardSize+caption)+(g.rows-1)*12<=604,'visible evaluation values must fit alongside equal boards');
}
