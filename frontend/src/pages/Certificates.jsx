import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Button, Card, EmptyState, LoadingScreen, PageHeader } from "../components/ui";

export default function Certificates() {
  const [certs, setCerts] = useState([]);
  const [images, setImages] = useState({}); // cert_id -> object URL
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let objectUrls = [];

    api.get("/certificates").then(async (res) => {
      setCerts(res.data);
      setLoading(false);

      // A plain <img src="..."> can't carry the Authorization header, so
      // fetch each certificate PNG through axios (which does attach it)
      // and turn the response into an object URL the <img> tag can use.
      for (const cert of res.data) {
        try {
          const imgRes = await api.get(`/certificates/${cert.cert_id}/image`, {
            responseType: "blob",
          });
          const url = URL.createObjectURL(imgRes.data);
          objectUrls.push(url);
          setImages((prev) => ({ ...prev, [cert.cert_id]: url }));
        } catch {
          // leave it unset; the UI just won't show that one image
        }
      }
    });

    return () => objectUrls.forEach((u) => URL.revokeObjectURL(u));
  }, []);

  if (loading) return <LoadingScreen label="Loading certificates…" />;

  return (
    <div>
      <PageHeader eyebrow="Achievements" title="My certificates" description="Earned automatically once every module (lessons + quiz) and the assignment are complete." />

      {certs.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon="🏆"
            title="No certificates yet"
            description="A certificate is issued automatically once you've completed every module in a course — its lessons AND its quiz, passed — AND your assignment has been approved."
          />
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {certs.map((cert) => (
            <Card key={cert.id}>
              <h2 className="font-display text-base font-bold text-ink-900">🎓 {cert.course_title}</h2>
              <div className="mt-1 text-xs text-ink-500">
                Certificate ID: {cert.cert_id} · Issued{" "}
                {new Date(cert.issued_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </div>
              {images[cert.cert_id] ? (
                <>
                  <img
                    src={images[cert.cert_id]}
                    alt={`Certificate for ${cert.course_title}`}
                    className="mt-4 w-full rounded-xl border border-ink-200"
                  />
                  <Button
                    as="a"
                    href={images[cert.cert_id]}
                    download={`dsiar-certificate-${cert.course_title.replace(/\s+/g, "_")}.png`}
                    className="mt-4"
                  >
                    ⬇ Download certificate (PNG)
                  </Button>
                </>
              ) : (
                <div className="mt-4 flex aspect-video items-center justify-center rounded-xl border border-dashed border-ink-200 text-sm text-ink-400">
                  Loading certificate image…
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
