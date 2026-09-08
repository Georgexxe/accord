const path=require('node:path');
const fs=require('node:fs');
const root=path.resolve(__dirname,'../frontend');
const out=path.join(root,'node_modules/.cache/accord-review-tests.cjs');
require(path.join(root,'node_modules/esbuild')).buildSync({entryPoints:[path.join(root,'tests/review.test.tsx')],bundle:true,platform:'node',format:'cjs',packages:'external',outfile:out,jsx:'automatic'});
const result=require('node:child_process').spawnSync(process.execPath,['--test',out],{stdio:'inherit',cwd:root});process.exit(result.status??1);
