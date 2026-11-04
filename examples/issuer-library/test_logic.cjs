const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(__dirname + '/logic.js', 'utf8') + '\nthis.logic = LibraryLogic;', context);
const {filterRuns, sortRuns, numberOf} = context.logic;
const rows = [
  {id:'missing',name:'Zeta',issuer:'Z',sector:'Energy',workflow:'Legal',date:'2024-01-01',period_kind:'Actual',completion:null,artifacts:[],metrics:{leverage:null,coverage:null}},
  {id:'zero',name:'Alpha',issuer:'A',sector:'Energy',workflow:'Credit',date:'2024-02-01',period_kind:'Actual',completion:0,artifacts:[],metrics:{leverage:{value:'0',basis:'Gross'},coverage:{value:'0'}}},
  {id:'gross',name:'Beta',issuer:'B',sector:'Auto',workflow:'Credit',date:'2023-01-01',period_kind:'Actual',completion:75,artifacts:[{available:true,state:'candidate'}],metrics:{leverage:{value:'5.96',basis:'Gross'},coverage:{value:'3.60'}}},
  {id:'net',name:'Gamma',issuer:'G',sector:'Auto',workflow:'Credit',date:'2022-01-01',period_kind:'Forecast',completion:100,artifacts:[],metrics:{leverage:{value:'2.2',basis:'Net'},coverage:{value:'4.5'}}}
];
test('missing values never become zero',()=>{
 assert.equal(numberOf(null),null); assert.equal(numberOf({value:''}),null); assert.equal(numberOf({value:'NaN'}),null); assert.equal(numberOf({value:'0'}),0);
 assert.deepEqual(Array.from(filterRuns(rows,{leverageMax:'0'}),r=>r.id),['zero']);
});
test('combined filters retain basis and period identity',()=>{
 assert.deepEqual(Array.from(filterRuns(rows,{sector:'Auto',basis:'Gross',leverageMin:'4',coverageMin:'3',period:'Actual'}),r=>r.id),['gross']);
 assert.equal(filterRuns(rows,{sector:'Auto',basis:'Net',leverageMin:'4'}).length,0);
});
test('unknown completeness, zero score and invalid threshold stay distinct',()=>{
 assert.deepEqual(Array.from(filterRuns(rows,{completion:'unassessed'}),r=>r.id),['missing']);
 assert.deepEqual(Array.from(filterRuns(rows,{completion:'75'}),r=>r.id),['gross','net']);
 assert.equal(filterRuns(rows,{leverageMin:'bad'}).length,0);
});
test('numeric sort keeps missing last in both directions without mutating input',()=>{
 assert.deepEqual(Array.from(sortRuns(rows,'leverage','asc'),r=>r.id),['zero','net','gross','missing']);
 assert.deepEqual(Array.from(sortRuns(rows,'leverage','desc'),r=>r.id),['gross','net','zero','missing']);
 assert.equal(rows[0].id,'missing');
});
test('search and report availability are conjunctive',()=>{
 assert.equal(filterRuns(rows,{search:'beta',availability:'report'}).length,1);
 assert.equal(filterRuns(rows,{search:'alpha',availability:'report'}).length,0);
});
