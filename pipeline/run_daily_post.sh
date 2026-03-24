#!/bin/bash
# run_daily_post.sh — triggered by OpenClaw cron
# Reads the next item from content_queue.json and posts it

WORKSPACE="/Users/leowu/.openclaw/workspace/atlas-of-culture"
QUEUE="$WORKSPACE/content_queue.json"

# Get next queued post
NEXT_DIR=$(python3 -c "
import json
with open('$QUEUE') as f:
    q = json.load(f)
posts = [p for p in q['queue'] if p.get('status') == 'ready']
if posts:
    print(posts[0]['content_dir'])
")

if [ -z "$NEXT_DIR" ]; then
  echo "Queue empty or no ready posts."
  exit 0
fi

echo "📬 Posting from: $NEXT_DIR"

# Determine image source: "imagen" = AI generated, else = viz code
IMAGE_SOURCE=$(python3 -c "
import json
with open('$NEXT_DIR/metadata.json') as f:
    m = json.load(f)
print(m.get('image_source', 'viz'))
")

if [ "$IMAGE_SOURCE" = "imagen" ]; then
  echo "🎨 Generating image via Imagen..."
  python3 "$WORKSPACE/pipeline/generate_image.py" "$NEXT_DIR" || exit 1
else
  echo "📊 Rendering data viz..."
  python3 "$WORKSPACE/pipeline/generate_viz.py" "$NEXT_DIR" || exit 1
fi

python3 "$WORKSPACE/pipeline/post_to_x.py" "$NEXT_DIR"
