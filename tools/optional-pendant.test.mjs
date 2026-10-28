import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeFoundation} from '../runtime/BP/scripts/core/extension-foundation.js';
import {installContent} from '../runtime/BP/scripts/core/extension-content.js';
import {furnitureItem,furnitureBlock,itemId,blockId,scriptedFurnitureItem} from '../runtime/BP/scripts/core/furniture.js';

test('an optional addon lamp uses the existing two-half furniture identity after validated registration',()=>{
 const source='optional_lamps',block=source+':green_pendant_lamp';
 const foundation=normalizeFoundation({furniture:[{block,kind:'pendant_lamp'}]},source,()=>true);
 installContent(source,[],foundation);
 const item=furnitureItem(block);assert.equal(item.kind,'pendant_lamp');
 assert.equal(itemId(item),block);assert.equal(blockId(item),block);
 assert.deepEqual(furnitureBlock(block),item);assert.deepEqual(scriptedFurnitureItem(block),item);
 assert.equal(foundation.furniture[0].half,'kaleidoscope_tavern:half');
 installContent(source,[],{});assert.equal(furnitureItem(block),undefined);
});

test('optional lamps cannot claim another addon or an incompatible half-state contract',()=>{
 assert.throws(()=>normalizeFoundation({furniture:[{block:'other:lamp',kind:'pendant_lamp'}]},'optional_lamps',()=>true));
 assert.throws(()=>normalizeFoundation({furniture:[{block:'optional_lamps:lamp',kind:'pendant_lamp',half:'optional_lamps:half'}]},'optional_lamps',()=>true));
});
