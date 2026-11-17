/** ScriptUI 2.2 API boundary double. It does not model client editing limits,
 * multiline rendering, focus, scrolling, text filtering or network timing. */
export * from '../../history/pre-release-0.6.29/tests/fake-ui.js';
import {ui} from '../../history/pre-release-0.6.29/tests/fake-ui.js';

export const DataDrivenScreenClosedReason=Object.freeze({ClientClosed:'ClientClosed',ServerClosed:'ServerClosed',UserBusy:'UserBusy'});

class ObservableValue{
 constructor(value,options={}){this.value=value;this.clientWritable=options.clientWritable===true;}
 getData(){return this.value;}
 setData(value){this.value=value;}
 writeFromClient(value){
  if(!this.clientWritable)throw Error('Observable is not client writable');
  if(typeof value!==typeof this.value)throw TypeError('Observable value type differs');
  this.value=value;
 }
}
export class ObservableString extends ObservableValue{}
export class ObservableNumber extends ObservableValue{}

export class CustomForm{
 constructor(player,title){this.player=player;this.heading=title;this.fields=[];this.buttons=[];this.showing=false;this.closeCalls=0;}
 textField(label,text,options={}){this.fields.push({type:'text',label,observable:text,options});return this;}
 dropdown(label,value,items,options={}){this.fields.push({type:'dropdown',label,observable:value,items,options});return this;}
 button(label,onClick,options={}){
  if(typeof onClick!=='function')throw TypeError('CustomForm.button requires a callback');
  this.buttons.push({label,onClick,options});return this;
 }
 isShowing(){return this.showing;}
 show(){
  if(this.showing)throw Error('FormVisibilityError');
  this.showing=true;ui.forms.push(this);
  return new Promise(resolve=>{this.resolve=resolve;});
 }
 close(){
  if(this.failClose)throw Error('INJECTED_FORM_CLOSE');
  if(!this.showing)throw Error('FormVisibilityError');
  this.closeCalls++;this.dismiss(DataDrivenScreenClosedReason.ServerClosed);
 }
 dismiss(reason=DataDrivenScreenClosedReason.ClientClosed){this.showing=false;this.resolve(reason);}
 edit(index,value){this.fields[index].observable.writeFromClient(value);}
 click(key){const button=this.buttons.find(row=>row.label.translate===key);if(!button)throw Error('Missing form button: '+key);button.onClick();}
}
