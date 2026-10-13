"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {compute, parseRatings, designEffect} = require("./icc.js");

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-10, String(a) + " != " + b);

test("systematic fixed rater offset: ICC(3,1)=1, absolute agreement lower", () => {
  const rows = parseRatings("1,2\n2,3\n3,4\n4,5");
  const r = compute(rows);
  near(r.ms_between, 10/3);
  near(r.ms_within, 0.5);
  near(r.ms_rater, 2);
  near(r.ms_error, 0);
  near(r.icc_1_1, 17/23);
  near(r.icc_1_k, .85);
  near(r.icc_2_1, 10/13);
  near(r.icc_2_k, 20/23);
  near(r.icc_3_1, 1);
  near(r.icc_3_k, 1);
});

test("identical raters, all ICCs one", () => {
  const r = compute([[1,1,1],[2,2,2],[4,4,4]]);
  for (const key of ["icc_1_1","icc_1_k","icc_2_1","icc_2_k","icc_3_1","icc_3_k"])
    near(r[key], 1);
});

test("constant ratings produce undefined estimates", () => {
  const r = compute([[1,1],[1,1],[1,1]]);
  assert.equal(r.icc_1_1, null);
  assert.equal(r.icc_2_1, null);
  assert.equal(r.icc_3_1, null);
});

test("header support, invalid matrix, nonfinite values", () => {
  assert.equal(parseRatings("R1,R2\n1,2\n3,4").length, 2);
  for (const text of ["1,2\n3,", "1,2\n3", "1,2\nNaN,3", "1,2\nInfinity,3"]) {
    assert.throws(() => parseRatings(text));
  }
  assert.throws(() => compute([[1,2],[3,NaN]]));
});

test("cluster design effect stays separate", () => {
  near(designEffect(6, 0.05), 1.25);
  assert.throws(() => designEffect(2, -0.1));
  assert.throws(() => designEffect(0, 0.1));
});
