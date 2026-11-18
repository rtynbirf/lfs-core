from lfs_core import autonomy as A
for ch in (None, 18):
    print(f"=== change_at={ch} ===")
    for c in (A.Follower, A.FollowerRandomFallback, A.Explorer):
        r = A.evaluate(c, change_at=ch)
        print(f"{c.__name__:24s}{r['verdict']:12s} on={r['quality_on']:.3f} off={r['quality_off']:.3f} "
              f"score={r['score_off']:.3f} post={r['post_change_score_off']} invalid={r['invalid_frac_off']:.2f} base={r['baseline_random_valid']:.3f}")
print("leak_check Explorer:", A.leak_check(A.Explorer), "| Follower:", A.leak_check(A.Follower))
print("=== zero-shot (Explorer) ===")
for k, v in A.zero_shot_test(A.Explorer).items(): print(k, v)
