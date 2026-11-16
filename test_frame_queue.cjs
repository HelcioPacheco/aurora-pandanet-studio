const assert=require('node:assert/strict'),FrameQueue=require('./static/frame-queue.js');
const frames=[],painted=[];const queue=new FrameQueue(fn=>(frames.push(fn),frames.length));
for(let i=0;i<100;i++)queue.enqueue(()=>painted.push(i));
assert.equal(frames.length,1);assert.deepEqual(painted,[]);frames.shift()();assert.deepEqual(painted,[99]);
queue.enqueue(()=>{painted.push(100);queue.enqueue(()=>painted.push(101));});frames.shift()();assert.deepEqual(painted,[99,100]);frames.shift()();assert.deepEqual(painted,[99,100,101]);
console.log('Frame queue passed: 100 inputs produce one frame with the latest state; scheduling continues without lost work.');
