/**
 * Smoke: node frontend/src/acl/ambiguityStreamBuffer.test.mjs
 */
import assert from "node:assert/strict";
import {
    finalizeAmbiguityStreamDisplay,
    mergeDisambiguationOptions,
    optionAttrsWellFormed,
    parseCompleteOptionsIncremental,
    processAmbiguityStreamDisplay,
    stripPartialAmbiguityTagSuffix,
} from "./ambiguityStreamBuffer.js";

assert.equal(stripPartialAmbiguityTagSuffix("olá <amb"), "olá ");

const mixedIntro =
    "Encontrei mais de uma referência.\n<ambiguity_options>\n<option discipline=\"python\" slug=\"a\" label=\"A\"/>";
const mixed = processAmbiguityStreamDisplay(mixedIntro);
assert.ok(mixed.proseBefore.includes("Encontrei"));
assert.equal(mixed.insideOpenBlock, true);

const postXml =
    'Intro.\n<ambiguity_options>\n<option discipline="a" slug="x" label="X"/>\n</ambiguity_options>\nPor favor, selecione uma delas.';
const post = processAmbiguityStreamDisplay(postXml);
assert.ok(post.proseBefore.includes("Intro"));
assert.ok(post.proseAfter.includes("selecione"));
assert.equal(post.blockClosed, true);
assert.equal(post.insideOpenBlock, false);

const incrementalXml =
    'Intro <ambiguity_options><option discipline="a" slug="1" label="Um"/><option discipline="b" slug="2" label="Dois"/>';
const inc = parseCompleteOptionsIncremental(incrementalXml);
assert.equal(inc.length, 2);

const pairCloseXml =
    '<ambiguity_options><option discipline="x" slug="y" label="Par"></option>';
const pairInc = parseCompleteOptionsIncremental(pairCloseXml);
assert.equal(pairInc.length, 1);
assert.equal(pairInc[0].slug, "y");

const openOnly =
    '<ambiguity_options><option discipline="a" slug="1" label="Sem fecho">';
assert.equal(parseCompleteOptionsIncremental(openOnly).length, 0);

const merged = mergeDisambiguationOptions(
    [{ title: "A", discipline: "p", slug: "a" }],
    [{ title: "B", discipline: "q", slug: "b" }],
);
assert.equal(merged.length, 2);

assert.equal(optionAttrsWellFormed('title="sem fecho'), false);

console.log("ambiguityStreamBuffer.test.mjs OK");
