'use strict';
const OutputLayout=(()=>{
 function grid(count,width,height,gap=12,caption=64){
  count=Math.max(1,Math.floor(count));width=Math.max(1,width);height=Math.max(1,height);
  let best={cols:1,rows:count,boardSize:0};
  for(let cols=1;cols<=count;cols++){
   const rows=Math.ceil(count/cols);
   const boardSize=Math.max(1,Math.min((width-gap*(cols-1))/cols,(height-gap*(rows-1))/rows-caption));
   if(boardSize>best.boardSize)best={cols,rows,boardSize:Math.floor(boardSize)};
  }
  return best;
 }
 return {grid};
})();
if(typeof module!=='undefined')module.exports=OutputLayout;
