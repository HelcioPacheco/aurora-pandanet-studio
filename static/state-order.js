'use strict';
const StateOrder=(()=>{
 function accept(current,next){
  const sameServer=current.server_id&&next.server_id?current.server_id===next.server_id:current.session_id===next.session_id;
  return !(sameServer&&Number.isFinite(current.revision)&&Number.isFinite(next.revision)&&next.revision<=current.revision);
 }
 function room(state){return Number(state.joining_room??state.room_id??0);}
 return {accept,room};
})();
if(typeof module!=='undefined')module.exports=StateOrder;
