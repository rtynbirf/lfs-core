from lfs_core import autonomy as A
for c in (A.Follower, A.FollowerRandomFallback, A.Explorer):
    print(c.__name__, A.evaluate(c))
